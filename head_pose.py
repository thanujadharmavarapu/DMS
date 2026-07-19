import time

import cv2
import numpy as np

import config


class HeadPoseEstimator:
    """
    Estimates 3D head pose (pitch, yaw, roll) via solvePnP, classifies the
    driver's head position into exactly one of NORMAL / LEFT / RIGHT
    (pitch/up-down is intentionally ignored per spec), and tracks how long
    the driver has been continuously looking away to trigger a
    "LOOK AWAY DETECTED" alert.
    """

    def __init__(self):

        # 3D Face Model
        self.model_points = np.array([
            (0.0, 0.0, 0.0),          # Nose
            (0.0, -63.6, -12.5),      # Chin
            (-43.3, 32.7, -26.0),     # Left Eye
            (43.3, 32.7, -26.0),      # Right Eye
            (-28.9, -28.9, -24.1),    # Left Mouth
            (28.9, -28.9, -24.1)      # Right Mouth
        ], dtype=np.float64)

        # MediaPipe Landmark IDs
        self.landmark_ids = [1, 152, 33, 263, 61, 291]

        # Yaw smoothing
        self.previous_yaw = None
        self.SMOOTHING = 0.60

        # ----------------------------
        # Calibration (baseline "straight ahead" yaw)
        # ----------------------------
        self.calibrated = False
        self.calibration_values = []
        self.CALIBRATION_TIME = config.CALIBRATION_TIME
        self.calibration_start = None
        self.baseline_yaw = 0.0

        # ----------------------------
        # Position classification (with hysteresis to avoid flicker)
        # ----------------------------
        self.ENTER_THRESHOLD = config.YAW_ENTER_THRESHOLD
        self.EXIT_THRESHOLD = config.YAW_EXIT_THRESHOLD
        self.current_position = "NORMAL"

        # ----------------------------
        # Look-away timer
        # ----------------------------
        self.LOOK_AWAY_TIME = config.LOOK_AWAY_TIME
        self.look_away_start = None
        self.look_away = False

    # ------------------------------------------

    def estimate(self, face_landmarks, frame):

        h, w, _ = frame.shape

        image_points = []

        for idx in self.landmark_ids:
            landmark = face_landmarks.landmark[idx]
            image_points.append((int(landmark.x * w), int(landmark.y * h)))

        image_points = np.array(image_points, dtype=np.float64)

        focal_length = w

        camera_matrix = np.array([
            [focal_length, 0, w / 2],
            [0, focal_length, h / 2],
            [0, 0, 1]
        ], dtype=np.float64)

        dist_coeffs = np.zeros((4, 1))

        success, rotation_vector, translation_vector = cv2.solvePnP(
            self.model_points,
            image_points,
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE
        )

        if not success:
            return None, image_points

        rotation_matrix, _ = cv2.Rodrigues(rotation_vector)

        angles, _, _, _, _, _ = cv2.RQDecomp3x3(rotation_matrix)

        pitch = angles[0]
        yaw = angles[1]
        roll = angles[2]

        # Smooth only yaw (used for left/right classification)
        if self.previous_yaw is None:
            self.previous_yaw = yaw

        yaw = (
            self.SMOOTHING * self.previous_yaw +
            (1 - self.SMOOTHING) * yaw
        )

        self.previous_yaw = yaw

        return (pitch, yaw, roll), image_points

    # ------------------------------------------
    # Calibration
    # ------------------------------------------

    def calibrate(self, yaw):
        """
        Call every frame during the calibration window while the driver
        looks straight ahead. Returns True once calibration is complete.
        """

        current = time.time()

        if self.calibration_start is None:
            self.calibration_start = current

        self.calibration_values.append(yaw)

        if current - self.calibration_start >= self.CALIBRATION_TIME:
            self.baseline_yaw = sum(self.calibration_values) / len(self.calibration_values)
            self.calibrated = True

        return self.calibrated

    # ------------------------------------------
    # Head Position Classification (LEFT / RIGHT / NORMAL only)
    # ------------------------------------------

    def get_head_position(self, yaw):

        if not self.calibrated:
            return "NORMAL"

        relative_yaw = yaw - self.baseline_yaw

        # Hysteresis: different thresholds to enter vs exit a turned state,
        # this prevents flickering when yaw sits right at the boundary.
        if self.current_position == "NORMAL":
            if relative_yaw > self.ENTER_THRESHOLD:
                self.current_position = "RIGHT"
            elif relative_yaw < -self.ENTER_THRESHOLD:
                self.current_position = "LEFT"
        else:
            if abs(relative_yaw) < self.EXIT_THRESHOLD:
                self.current_position = "NORMAL"

        return self.current_position

    # ------------------------------------------
    # Look-Away Detection
    # ------------------------------------------

    def detect_look_away(self, head_position):

        current = time.time()

        if head_position in ("LEFT", "RIGHT"):

            if self.look_away_start is None:
                self.look_away_start = current

            elapsed = current - self.look_away_start

            if elapsed >= self.LOOK_AWAY_TIME:
                self.look_away = True

        else:
            # Looking forward again -> immediate reset
            self.look_away_start = None
            self.look_away = False

        return self.look_away

    # ------------------------------------------

    def reset(self):
        """Reset per-frame timers/state (NOT calibration) e.g. when face is lost."""
        self.previous_yaw = None
        self.current_position = "NORMAL"
        self.look_away_start = None
        self.look_away = False
