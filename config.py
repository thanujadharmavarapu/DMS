# ==============================
# Driver Monitoring System Config
# ==============================

# Camera
CAMERA_INDEX = 0
WINDOW_NAME = "Driver Monitoring System"

# Face Mesh
MAX_NUM_FACES = 1
REFINE_LANDMARKS = True
MIN_DETECTION_CONFIDENCE = 0.5
MIN_TRACKING_CONFIDENCE = 0.5

# ------------------------------
# Calibration
# ------------------------------
CALIBRATION_TIME = 3  # seconds

# ------------------------------
# Drowsiness (EAR / PERCLOS)
# ------------------------------
EAR_CLOSE_RATIO = 0.82   # fraction of calibrated "normal" EAR -> eyes considered closed
EAR_OPEN_RATIO = 0.88    # fraction of calibrated "normal" EAR -> eyes considered open
FATIGUE_TIME = 3         # seconds eyes must stay closed continuously to trigger fatigue

# ------------------------------
# Head Pose / Look-Away
# ------------------------------
YAW_ENTER_THRESHOLD = 15   # degrees off-center to ENTER left/right state
YAW_EXIT_THRESHOLD = 10    # degrees off-center to EXIT back to normal (hysteresis)
LOOK_AWAY_TIME = 5         # seconds looking away continuously to trigger look-away alert

# Alarm
ALARM_SOUND = "assets/alarm.wav"

# Drawing
TEXT_COLOR = (0, 255, 0)
WARNING_COLOR = (0, 0, 255)
FONT_SCALE = 0.8
THICKNESS = 2
