import time

import config


class HeadPoseEstimator:
    """
    Classifies the driver's head position into exactly one of
    NORMAL / LEFT / RIGHT and tracks how long the driver has been
    continuously looking away to trigger a "LOOK AWAY DETECTED" alert.

    NOTE ON METHOD: an earlier version derived yaw from
    cv2.solvePnP + cv2.RQDecomp3x3. That Euler-angle decomposition is
    known to behave asymmetrically for larger rotations in one direction
    (a real OpenCV quirk), which is why turning LEFT could fail to
    register while RIGHT worked fine. This version instead uses a
    simple, symmetric geometric signal: where the nose sits horizontally
    between the two cheek landmarks. It has no directional bias and
    needs no matrix decomposition at all.
    """

    # MediaPipe FaceMesh landmark IDs
    NOSE_TIP = 1
    LEFT_CHEEK = 234
    RIGHT_CHEEK = 454

    def __init__(self):

        # Ratio smoothing
        self.previous_ratio = None
        self.SMOOTHING = 0.60

        # ----------------------------
        # Calibration (baseline "straight ahead" ratio)
        # ----------------------------
        self.calibrated = False
        self.calibration_values = []
        self.CALIBRATION_TIME = config.CALIBRATION_TIME
        self.calibration_start = None
        self.baseline_ratio = 0.5

        # ----------------------------
        # Position classification (with hysteresis to avoid flicker)
        # ----------------------------
        self.ENTER_THRESHOLD = config.HORIZONTAL_ENTER_THRESHOLD
        self.EXIT_THRESHOLD = config.HORIZONTAL_EXIT_THRESHOLD
        self.current_position = "NORMAL"

        # ----------------------------
        # Look-away timer
        # ----------------------------
        self.LOOK_AWAY_TIME = config.LOOK_AWAY_TIME
        self.look_away_start = None
        self.look_away = False

    # ------------------------------------------
    # Geometry
    # ------------------------------------------

    def compute_horizontal_ratio(self, face_landmarks, frame):
        """
        Returns a value in ~[0, 1]: where the nose tip sits horizontally
        between the left cheek and right cheek landmarks.
        ~0.5 = centered (looking straight at the camera).
        Moves toward 0 or 1 as the head turns to either side.
        This is symmetric by construction, so LEFT and RIGHT behave
        identically -- no directional bias like the old yaw method had.
        """

        w = frame.shape[1]

        nose_x = face_landmarks.landmark[self.NOSE_TIP].x * w
        left_x = face_landmarks.landmark[self.LEFT_CHEEK].x * w
        right_x = face_landmarks.landmark[self.RIGHT_CHEEK].x * w

        face_width = right_x - left_x

        if abs(face_width) < 1e-6:
            return self.baseline_ratio  # degenerate frame, hold steady

        ratio = (nose_x - left_x) / face_width

        if self.previous_ratio is None:
            self.previous_ratio = ratio

        ratio = (
            self.SMOOTHING * self.previous_ratio +
            (1 - self.SMOOTHING) * ratio
        )

        self.previous_ratio = ratio

        return ratio

    # ------------------------------------------
    # Calibration
    # ------------------------------------------

    def calibrate(self, ratio):
        """
        Call every frame during the calibration window while the driver
        looks straight ahead. Returns True once calibration is complete.
        """

        current = time.time()

        if self.calibration_start is None:
            self.calibration_start = current

        self.calibration_values.append(ratio)

        if current - self.calibration_start >= self.CALIBRATION_TIME:
            self.baseline_ratio = sum(self.calibration_values) / len(self.calibration_values)
            self.calibrated = True

        return self.calibrated

    # ------------------------------------------
    # Head Position Classification (LEFT / RIGHT / NORMAL only)
    # ------------------------------------------

    def get_head_position(self, ratio):

        if not self.calibrated:
            return "NORMAL"

        relative = ratio - self.baseline_ratio

        if config.INVERT_HEAD_TURN:
            relative = -relative

        # Hysteresis: different thresholds to enter vs exit a turned state,
        # this prevents flickering when the ratio sits right at the boundary.
        # A smaller ratio than baseline means the nose has drifted toward
        # the left cheek landmark -> head turned toward image-left, and
        # vice versa for RIGHT.
        if self.current_position == "NORMAL":
            if relative < -self.ENTER_THRESHOLD:
                self.current_position = "LEFT"
            elif relative > self.ENTER_THRESHOLD:
                self.current_position = "RIGHT"
        else:
            if abs(relative) < self.EXIT_THRESHOLD:
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
        self.previous_ratio = None
        self.current_position = "NORMAL"
        self.look_away_start = None
        self.look_away = False
