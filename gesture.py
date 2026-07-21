"""
gesture.py
----------
STEP 4: Hand landmark detection using MediaPipe Hands.

WHAT THIS STEP DOES (and nothing more):
  - Feeds each camera frame into MediaPipe's hand detector.
  - MediaPipe finds up to 2 hands and returns 21 landmark points per hand
    (fingertips, knuckles, wrist, etc.) as normalized (0.0-1.0) coordinates.
  - We draw the landmarks + connecting skeleton lines onto the frame so
    you can SEE that detection is working.

Actual GESTURE RECOGNITION (turning landmarks into "this is a fist" or
"this is a pinch") comes in Step 5. This step is purely: "can the
computer see my hand and find its joints?"
"""

import cv2
import mediapipe as mp


class HandTracker:
    """Wraps MediaPipe Hands with a simple process/draw interface."""

    def __init__(self, max_num_hands=2, detection_confidence=0.7, tracking_confidence=0.5):
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,       # False = optimized for video (tracks between frames)
            max_num_hands=max_num_hands,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
        )

        self.latest_results = None

    def process(self, frame_bgr):
        """
        Runs hand detection on a single frame.
        frame_bgr: OpenCV frame (BGR color order, as returned by CameraManager).
        Returns MediaPipe's results object (also stored as self.latest_results).
        """
        # MediaPipe expects RGB, OpenCV gives us BGR -- convert first.
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        # Marking the array as not writeable is a small MediaPipe
        # performance optimization (avoids an internal copy).
        frame_rgb.flags.writeable = False
        results = self.hands.process(frame_rgb)
        frame_rgb.flags.writeable = True

        self.latest_results = results
        return results

    def draw_landmarks(self, frame_bgr, results):
        """Draws the 21-point hand skeleton directly onto frame_bgr (in place)
        and also returns it, for convenience."""
        if results and results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                self.mp_drawing.draw_landmarks(
                    frame_bgr,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing_styles.get_default_hand_landmarks_style(),
                    self.mp_drawing_styles.get_default_hand_connections_style(),
                )
        return frame_bgr

    def get_hand_count(self, results):
        """Convenience helper: how many hands were detected this frame."""
        if results and results.multi_hand_landmarks:
            return len(results.multi_hand_landmarks)
        return 0

    def get_landmark_pixel_positions(self, results, frame_width, frame_height):
        """
        Converts MediaPipe's normalized (0.0-1.0) landmark coordinates into
        actual pixel positions for a frame of the given size.

        Returns a list of hands, where each hand is a list of 21 (x, y)
        pixel tuples, indexed by MediaPipe's landmark numbering
        (0 = wrist, 4 = thumb tip, 8 = index fingertip, etc.)
        We'll use this indexing heavily in Step 5 for gesture recognition.
        """
        all_hands = []
        if results and results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                points = [
                    (int(lm.x * frame_width), int(lm.y * frame_height))
                    for lm in hand_landmarks.landmark
                ]
                all_hands.append(points)
        return all_hands

    def get_landmark_normalized_positions(self, results):
        """
        Same idea as get_landmark_pixel_positions, but keeps coordinates
        as normalized 0.0-1.0 floats instead of converting to camera-frame
        pixels. This is what we use to map a fingertip onto the GAME
        WINDOW (1280x720), which is a different size/aspect ratio than
        the camera frame -- so pixel coordinates from the camera would be
        the wrong scale.
        """
        all_hands = []
        if results and results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                points = [(lm.x, lm.y) for lm in hand_landmarks.landmark]
                all_hands.append(points)
        return all_hands

    def close(self):
        self.hands.close()


# ---------------------------------------------------------------------------
# STEP 5: Turning raw landmarks into named gestures
# ---------------------------------------------------------------------------

import math
from collections import deque


# Landmark index reference (MediaPipe's fixed numbering, 0-20):
#   0 = wrist
#   4 = thumb tip        3 = thumb IP joint
#   8 = index tip         6 = index PIP joint
#   12 = middle tip        10 = middle PIP joint
#   16 = ring tip          14 = ring PIP joint
#   20 = pinky tip          18 = pinky PIP joint
#   9  = middle finger MCP (used as a stable "palm center" reference)
#   17 = pinky MCP (used to judge if the thumb is sticking outward)

FINGER_TIPS = [8, 12, 16, 20]
FINGER_PIPS = [6, 10, 14, 18]


def _distance(point_a, point_b):
    return math.hypot(point_a[0] - point_b[0], point_a[1] - point_b[1])


class GestureRecognizer:
    """
    Classifies a single frame's hand landmarks into a named gesture, then
    SMOOTHS the result over several frames so a momentary misread (e.g.
    MediaPipe jitters for one frame) doesn't register as a fake gesture.

    Recognized gestures: "open_palm", "fist", "pinch", "victory",
    "thumbs_up", "two_hands_open", "none", "unknown"
    """

    def __init__(self, history_length=6, confirm_threshold=4, pinch_threshold=0.45):
        # How many recent frames we remember, and how many of those must
        # agree before we "confirm" a gesture. Higher threshold = more
        # stable but slightly more laggy. 4 out of 6 frames is a good
        # beginner-friendly balance (~65ms of delay at 60fps).
        self.history = deque(maxlen=history_length)
        self.confirm_threshold = confirm_threshold
        self.pinch_threshold = pinch_threshold
        self.confirmed_gesture = "none"

    def _fingers_extended(self, landmarks):
        """Returns [thumb, index, middle, ring, pinky] as True/False."""
        # Thumb: extended if its tip is much farther from the pinky-MCP
        # than its inner joint is -- i.e. it's sticking outward from the
        # palm. This avoids needing to know if it's a left or right hand.
        thumb_tip_dist = _distance(landmarks[4], landmarks[17])
        thumb_ip_dist = _distance(landmarks[3], landmarks[17])
        thumb_extended = thumb_tip_dist > thumb_ip_dist * 1.15

        # Other 4 fingers: extended if the tip is above the knuckle below
        # it (smaller y = higher on screen, since y grows downward).
        other_fingers = [
            landmarks[tip][1] < landmarks[pip][1]
            for tip, pip in zip(FINGER_TIPS, FINGER_PIPS)
        ]
        return [thumb_extended] + other_fingers

    def _classify_single_hand(self, landmarks):
        # Hand size reference (wrist to middle-finger knuckle) so our
        # pinch distance threshold scales with how close/far the hand is
        # from the camera, instead of being a fixed pixel count.
        hand_scale = _distance(landmarks[0], landmarks[9])
        if hand_scale < 1:
            return "unknown"

        pinch_distance = _distance(landmarks[4], landmarks[8]) / hand_scale
        if pinch_distance < self.pinch_threshold:
            return "pinch"

        thumb, index, middle, ring, pinky = self._fingers_extended(landmarks)

        if thumb and index and middle and ring and pinky:
            return "open_palm"
        if not any([thumb, index, middle, ring, pinky]):
            return "fist"
        if index and middle and not ring and not pinky:
            return "victory"
        if thumb and not any([index, middle, ring, pinky]):
            return "thumbs_up"

        return "unknown"

    def _classify_frame(self, hands_landmarks_list):
        """hands_landmarks_list: output of HandTracker.get_landmark_pixel_positions()"""
        if len(hands_landmarks_list) == 0:
            return "none"

        if len(hands_landmarks_list) >= 2:
            # Two hands: currently we only care about "both palms wide
            # open" (this will become the BOMB gesture in a later step).
            gestures = [self._classify_single_hand(h) for h in hands_landmarks_list]
            if all(g == "open_palm" for g in gestures):
                return "two_hands_open"
            return "unknown"

        return self._classify_single_hand(hands_landmarks_list[0])

    def update(self, hands_landmarks_list):
        """
        Call this once per frame with the current landmarks. Returns the
        SMOOTHED/confirmed gesture name (not necessarily this frame's raw
        read -- it only changes once a new gesture is consistent).
        """
        raw_gesture = self._classify_frame(hands_landmarks_list)
        self.history.append(raw_gesture)

        if self.history.count(raw_gesture) >= self.confirm_threshold:
            self.confirmed_gesture = raw_gesture

        return self.confirmed_gesture