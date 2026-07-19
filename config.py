# ==============================
# Driver Monitoring System Config
# ==============================

# Camera
CAMERA_INDEX = 0
WINDOW_NAME = "Driver Monitoring System"
SHOW_CAMERA_PREVIEW = False   # True -> also pop a raw cv2 debug window

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
# Thresholds are in "nose-to-cheek ratio" units (see head_pose.py), not
# degrees -- roughly, the fraction of face-width the nose has drifted
# off-center. ~0.05-0.06 is a clearly-turned head for a typical webcam.
HORIZONTAL_ENTER_THRESHOLD = 0.055   # ENTER a turned (LEFT/RIGHT) state
HORIZONTAL_EXIT_THRESHOLD = 0.035    # EXIT back to NORMAL (hysteresis)
INVERT_HEAD_TURN = False             # flip if LEFT/RIGHT ever read backwards
                                      # for your specific camera setup
LOOK_AWAY_TIME = 3         # seconds looking away continuously to trigger look-away alert

# Alarm
ALARM_SOUND = "assets/alarm.wav"

# ------------------------------
# Threading / Queue (Camera <-> GUI bridge)
# ------------------------------
QUEUE_MAXSIZE = 5          # small ring buffer; GUI only ever needs the latest
CAMERA_PUSH_FPS = 30       # rate at which the camera thread pushes state to the queue
GUI_TICK_MS = 20           # root.after() cadence for the dashboard (~50 Hz)

# ------------------------------
# Dashboard (Tkinter Safety Console)
# ------------------------------
DASH_WINDOW_TITLE = "Advanced Safety Dashboard"
DASH_WIDTH = 1000
DASH_HEIGHT = 650

SPEED_UNIT = "KM/H"
MAX_SPEED = 80              # km/h, target cruising speed when NORMAL

# Rate-based motion (km/h per second) instead of percentage easing.
# This gives a constant, predictable ramp rather than a fast-then-slow
# exponential curve -- i.e. genuinely gradual, controlled braking.
ACCEL_RATE = 12.0           # km/h per second, cruise acceleration
AEB_DECEL_RATE = 16.0       # km/h per second, gradual AEB braking rate
                            # (80 -> 0 takes ~5s: firm but not a slam-stop)

HAZARD_BLINK_MS = 400        # hazard light blink half-period

VIBRATION_AMPLITUDE = 4       # px shake amplitude for steering wheel
VIBRATION_SPEED = 0.6         # radians added to vibration phase per tick
WAVE_MAX_RADIUS = 70          # cyan ripple max radius before it resets
WAVE_GROWTH = 2.5             # px growth per tick

# Dark automotive theme
BG_DARK = "#0b0e14"
PANEL_DARK = "#12161f"
GRID_LINE = "#1c2230"
TEXT_LIGHT = "#e6e9ef"
TEXT_DIM = "#7a8296"

ACCENT_GREEN = "#33d17a"
ACCENT_CYAN = "#22d3ee"
ACCENT_AMBER = "#f5a623"
ACCENT_RED = "#ef4444"
CAR_BODY_COLOR = "#232a3a"
WHEEL_COLOR = "#0d1017"

# Drawing (legacy cv2 overlay, still used by the optional preview window)
TEXT_COLOR = (0, 255, 0)
WARNING_COLOR = (0, 0, 255)
FONT_SCALE = 0.8
THICKNESS = 2
