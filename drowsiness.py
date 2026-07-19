import math
import time

import config


class DrowsinessDetector:
    """
    Handles EAR (Eye Aspect Ratio) based PERCLOS fatigue detection.

    Flow:
      1. calibrate() is called every frame for CALIBRATION_TIME seconds
         while the driver looks straight with eyes open -> establishes
         a personal baseline EAR.
      2. Once calibrated, detect() is called every frame and returns
         True/False for whether the driver is currently "FATIGUE DETECTED".
    """

    def __init__(self):

        # ----------------------------
        # Calibration
        # ----------------------------
        self.calibrated = False
        self.calibration_values = []
        self.CALIBRATION_TIME = config.CALIBRATION_TIME
        self.calibration_start = None
        self.normal_ear = 0.0

        # ----------------------------
        # Hysteresis Thresholds (set after calibration)
        # ----------------------------
        self.EAR_CLOSE_THRESHOLD = 0.0
        self.EAR_OPEN_THRESHOLD = 0.0

        # ----------------------------
        # Eye Close Timer
        # ----------------------------
        self.CLOSED_TIME = config.FATIGUE_TIME
        self.eye_closed_start = None
        self.fatigue = False

        # ----------------------------
        # EAR Smoothing
        # ----------------------------
        self.previous_ear = None
        self.SMOOTHING = 0.60

    # -------------------------------------

    def distance(self, p1, p2):
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

    # -------------------------------------

    def calculate_ear(self, eye):
        A = self.distance(eye[1], eye[5])
        B = self.distance(eye[2], eye[4])
        C = self.distance(eye[0], eye[3])

        if C == 0:
            return 0

        return (A + B) / (2 * C)

    # -------------------------------------

    def get_average_ear(self, left_eye, right_eye):

        left = self.calculate_ear(left_eye)
        right = self.calculate_ear(right_eye)

        ear = (left + right) / 2

        if self.previous_ear is None:
            self.previous_ear = ear

        ear = (
            self.SMOOTHING * self.previous_ear +
            (1 - self.SMOOTHING) * ear
        )

        self.previous_ear = ear

        return ear

    # -------------------------------------
    # Calibration
    # -------------------------------------

    def calibrate(self, ear):
        """
        Call every frame during the calibration window.
        Returns True once calibration is complete.
        """

        current = time.time()

        if self.calibration_start is None:
            self.calibration_start = current

        self.calibration_values.append(ear)

        elapsed = current - self.calibration_start

        if elapsed >= self.CALIBRATION_TIME:

            self.normal_ear = sum(self.calibration_values) / len(self.calibration_values)

            self.EAR_CLOSE_THRESHOLD = self.normal_ear * config.EAR_CLOSE_RATIO
            self.EAR_OPEN_THRESHOLD = self.normal_ear * config.EAR_OPEN_RATIO

            self.calibrated = True

        return self.calibrated

    def calibration_time_left(self):
        if self.calibration_start is None:
            return self.CALIBRATION_TIME
        remaining = self.CALIBRATION_TIME - (time.time() - self.calibration_start)
        return max(0, remaining)

    # -------------------------------------
    # Fatigue Detection
    # -------------------------------------

    def detect(self, ear):

        if not self.calibrated:
            return False

        current = time.time()

        if ear < self.EAR_CLOSE_THRESHOLD:

            if self.eye_closed_start is None:
                self.eye_closed_start = current

            elapsed = current - self.eye_closed_start

            if elapsed >= self.CLOSED_TIME:
                self.fatigue = True

        elif ear > self.EAR_OPEN_THRESHOLD:
            # Eyes confirmed open again -> immediate reset (no lag on recovery)
            self.eye_closed_start = None
            self.fatigue = False

        return self.fatigue

    # -------------------------------------

    def reset(self):
        """Reset per-frame timers/state (NOT calibration) e.g. when face is lost."""
        self.eye_closed_start = None
        self.fatigue = False
        self.previous_ear = None
