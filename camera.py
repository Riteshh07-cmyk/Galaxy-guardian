"""
camera.py
---------
STEP 3: Threaded webcam capture.

WHY A SEPARATE THREAD?
Reading from a webcam (cv2.VideoCapture.read()) can take a few
milliseconds each call. If we did that directly inside the main game
loop, the game would stutter every time it waited on the camera.

So instead: a background thread continuously grabs frames from the
webcam as fast as it can and stores only the LATEST one. The game loop
just asks CameraManager "what's the latest frame?" -- it never waits.

This is the same producer/consumer pattern used in most real-time
computer vision apps.
"""

import threading

import cv2

import settings


class CameraManager:
    """Runs webcam capture on a background thread and exposes the
    most recent frame in a thread-safe way."""

    def __init__(self, camera_index=None):
        self.camera_index = (
            camera_index if camera_index is not None else settings.CAMERA_INDEX
        )

        self.cap = None
        self.latest_frame = None          # most recent frame (BGR, numpy array)
        self.frame_lock = threading.Lock()  # protects latest_frame from race conditions

        self.running = False
        self.thread = None

        self.connected = False
        self.error_message = None

    def start(self):
        """Opens the camera and starts the background capture thread."""
        self.cap = cv2.VideoCapture(self.camera_index)

        # Ask the camera for a specific resolution. Not all cameras honor
        # this exactly, but most will get close.
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.CAMERA_HEIGHT)

        if not self.cap.isOpened():
            self.connected = False
            self.error_message = (
                f"Could not open camera index {self.camera_index}. "
                "Is a webcam plugged in and not in use by another app?"
            )
            print(f"[camera] ERROR: {self.error_message}")
            return

        self.connected = True
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        print("[camera] Started successfully.")

    def _capture_loop(self):
        """Runs on the background thread. Reads frames as fast as possible."""
        while self.running:
            ok, frame = self.cap.read()
            if not ok:
                # Camera briefly failed to return a frame -- could be a
                # dropped USB frame. Don't crash, just skip this cycle.
                continue

            # Mirror the frame horizontally so movement feels natural
            # (move your hand right -> it appears on the right, like a mirror)
            frame = cv2.flip(frame, 1)

            with self.frame_lock:
                self.latest_frame = frame

    def get_latest_frame(self):
        """Thread-safe read of the most recent frame. Returns None if
        no frame has been captured yet (e.g. camera just started)."""
        with self.frame_lock:
            if self.latest_frame is None:
                return None
            return self.latest_frame.copy()

    def stop(self):
        """Stops the capture thread and releases the camera cleanly."""
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=1.0)
        if self.cap is not None:
            self.cap.release()
        print("[camera] Stopped and released.")