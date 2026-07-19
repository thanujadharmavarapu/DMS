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

# Drowsiness
EAR_THRESHOLD = 0.25
CONSECUTIVE_FRAMES = 20

# Alarm
ALARM_SOUND = "assets/alarm.wav"

# Drawing
TEXT_COLOR = (0, 255, 0)
WARNING_COLOR = (0, 0, 255)
FONT_SCALE = 1
THICKNESS = 2