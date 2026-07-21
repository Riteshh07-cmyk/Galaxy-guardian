"""
utils.py
--------
Small shared helper functions used across multiple files.
Starting small on purpose -- we'll add more here as later steps need them
(e.g. lerp/easing helpers, vector math, collision helpers).
"""

import cv2
import pygame


def cv2_frame_to_pygame_surface(frame):
    """
    Converts an OpenCV frame (numpy array, BGR color order, shape HxWx3)
    into a pygame.Surface (RGB color order) that can be blit() onto the
    game screen.

    Why this is needed: OpenCV and Pygame store color channels in a
    different order (BGR vs RGB) and use different array/surface formats,
    so we can't just hand one library's image to the other directly.
    """
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    # OpenCV arrays are indexed [row, col] i.e. [height, width].
    # Pygame's surfarray expects [width, height], so we transpose.
    surface = pygame.surfarray.make_surface(rgb_frame.swapaxes(0, 1))
    return surface