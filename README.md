# Edge-AI Driver Monitoring System (DMS)

Real-time driver fatigue and distraction detection, built with OpenCV +
MediaPipe Face Mesh, wired into a dark-mode Tkinter "Advanced Safety
Dashboard" (top-down car view, hazard lights, brake lamps, steering-wheel
vibration, and a speed gauge with simulated Automatic Emergency Braking).

The camera pipeline runs on a background thread; the dashboard runs on the
main thread. They talk to each other only through a thread-safe
`queue.Queue`, so the UI never freezes and frames never drop waiting on
the GUI.

---

## 1. Features

- **Fatigue detection** — Eye Aspect Ratio (EAR) based PERCLOS. If the
  driver's eyes stay closed continuously for **3 seconds**, state becomes
  `FATIGUE DETECTED`.
- **Distraction detection** — head-turn detection using a symmetric
  nose/cheek landmark ratio (no solvePnP angle quirks). If the driver
  looks away (LEFT or RIGHT) continuously for **3 seconds**, state becomes
  `LOOK AWAY DETECTED`.
- **No-face safety state** — if the driver isn't visible to the camera at
  all, the system treats this as a precaution and slows the vehicle down.
- **Auto-calibration** — on startup, look straight ahead with your eyes
  open for ~3 seconds so the system can learn your personal baseline EAR
  and head position.
- **Dashboard**
  - Top-down car with 4 amber hazard lights (blink during Fatigue/No-Face)
  - Rear brake lamp bar (solid red during AEB braking)
  - Steering wheel that shakes + emits cyan ripple waves when distracted
  - Speed gauge (km/h) with **gradual**, rate-based AEB braking — not an
    instant stop
  - Clean status readout: `EAR`, `Head Position`, `STATUS`
- **Audio alarm** — loops during `FATIGUE` or `DISTRACTED`, stops
  immediately once the driver is alert again. Fails safe (prints a
  warning and disables itself) if the sound file is missing.
- **Graceful shutdown** — closing the dashboard window stops the camera
  thread and releases the webcam cleanly; no zombie `cv2` windows or
  hung processes.

---

## 2. Project Structure

```
dms/
├── main.py            # Entry point — wires everything together, run this
├── config.py           # ALL tunable thresholds, colors, sizes in one place
├── camera_worker.py     # Background thread: webcam + MediaPipe + EAR/head-turn
├── dashboard.py         # Tkinter dashboard (main thread only)
├── detector.py          # FaceDetector — MediaPipe Face Mesh wrapper, eye landmarks
├── drowsiness.py        # DrowsinessDetector — EAR calc, calibration, fatigue timer
├── head_pose.py         # HeadPoseEstimator — nose/cheek ratio, LEFT/RIGHT/NORMAL
├── alert.py             # Alarm — looping sound, fails safe if file missing
├── utils.py             # Small drawing/math helpers
└── assets/
    └── alarm.wav        # (you provide this — see Setup step 4)
```

---

## 3. Requirements

- Python 3.9–3.11 (3.10 recommended)
- A webcam
- Packages:
  - `opencv-python`
  - `mediapipe`
  - `pygame` (for the alarm sound)
  - `numpy`
  - `tkinter` (ships with standard Python on Windows/macOS; on some Linux
    distros install it separately — see Troubleshooting)

---

## 4. Setup

**1. Get the files**
Put all the `.py` files listed above into one folder.

**2. Create a virtual environment (recommended)**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

**3. Install dependencies**
```bash
pip install opencv-python mediapipe pygame numpy
```

**4. Add an alarm sound**
```
dms/
└── assets/
    └── alarm.wav
```
Any short `.wav` loop works. If you skip this, the app still runs — the
alarm just disables itself (with a console warning) and you rely on the
visual dashboard alert only.

**5. (Linux only) Install Tkinter if missing**
```bash
sudo apt install python3-tk
```

---

## 5. How to Run

```bash
python main.py
```

This opens **one window**: the Advanced Safety Dashboard. There is no
separate raw camera window by default (the webcam runs invisibly in the
background thread) — see `config.SHOW_CAMERA_PREVIEW` below if you want a
debug view of what the camera sees.

### First few seconds — Calibration
When the app starts, **look straight at the camera with your eyes open**
for about 3 seconds. This is silent on the dashboard (state shows
`CALIBRATING`) but it's establishing your personal baseline — skipping
this or moving around during it will make fatigue/distraction detection
less accurate.

### After calibration
- Sit normally → dashboard shows `NORMAL`, speed eases up to cruising
  speed, hazards and brake lamps off.
- Close your eyes for 3+ continuous seconds → `FATIGUE DETECTED`: hazards
  flash amber, brake lamps go solid red, AEB gradually brings speed to 0,
  steering wheel vibrates, alarm sounds.
- Turn your head left or right and hold it for 3+ seconds → `LOOK AWAY
  DETECTED`: steering wheel vibrates with cyan ripple waves, alarm
  sounds, speed is unaffected.
- Look back / open your eyes → alarm and effects clear **immediately**,
  state returns to `NORMAL`.
- Step out of frame → `NO FACE DETECTED`, treated as a safety precaution
  (hazards + gradual braking), alarm off.

### Quitting
Just close the dashboard window (the X button). This triggers a clean
shutdown: the camera thread is signaled to stop, the webcam is released,
and then the window closes. Don't force-kill the process if you can help
it — closing normally avoids leaving the webcam locked by the OS.

---

## 6. Configuration Cheat-Sheet (`config.py`)

Everything you'd want to tune for a demo lives here — no need to touch
the logic files.

| Setting | What it does | Current default |
|---|---|---|
| `FATIGUE_TIME` | Seconds of continuous eye closure before alarm | `3` |
| `LOOK_AWAY_TIME` | Seconds of continuous head-turn before alarm | `3` |
| `HORIZONTAL_ENTER_THRESHOLD` / `_EXIT_THRESHOLD` | How far the head must turn to register LEFT/RIGHT (hysteresis prevents flicker) | `0.055` / `0.035` |
| `INVERT_HEAD_TURN` | Flip if LEFT/RIGHT ever read backwards for your camera | `False` |
| `MAX_SPEED` | Cruising speed target (km/h) | `80` |
| `ACCEL_RATE` / `AEB_DECEL_RATE` | km/h-per-second ramp rates — controls how gradual acceleration/braking feels | `12.0` / `16.0` |
| `CALIBRATION_TIME` | Seconds of the startup calibration window | `3` |
| `SHOW_CAMERA_PREVIEW` | Set `True` to also pop a raw cv2 debug window showing EAR/state overlaid on the live feed | `False` |
| `CAMERA_INDEX` | Which webcam to use (`0` = default) | `0` |

---

## 7. Architecture Notes (why it doesn't freeze)

- `camera_worker.py`'s `CameraWorker.run()` executes on a background
  `threading.Thread` (started in `main.py`). It never imports or touches
  `tkinter`.
- It pushes small state dicts (`{'state', 'ear', 'head_position',
  'timestamp'}`) into a `queue.Queue` using non-blocking
  `put_nowait()`, dropping the oldest entry if the queue is momentarily
  full.
- `dashboard.py`'s `SafetyDashboard.tick()` is scheduled with
  `root.after(config.GUI_TICK_MS, self.tick)` — pure Tkinter-thread code.
  Each tick drains the queue down to the freshest snapshot with
  `get_nowait()`, updates animated values (speed, hazards, vibration),
  and redraws.
- Because both sides only ever use non-blocking queue operations,
  neither thread can stall the other — the GUI can't freeze the camera
  loop, and camera hiccups can't freeze the GUI.
- Closing the window calls `App.shutdown()` in `main.py`, which sets a
  `threading.Event`, stops the alarm, `join()`s the camera thread (with a
  2s timeout so `cv2.VideoCapture.release()` gets a chance to run), and
  only then destroys the Tk root.

---

## 8. Troubleshooting

**`ModuleNotFoundError: No module named 'tkinter'`**
Tkinter isn't bundled with your Python install. On Debian/Ubuntu:
`sudo apt install python3-tk`. On other systems, reinstall Python from
[python.org](https://python.org) with the "tcl/tk" option checked.

**Webcam window is black / `cv2.VideoCapture` fails**
Another app may be holding the camera, or `CAMERA_INDEX` is wrong. Try
`CAMERA_INDEX = 1` in `config.py` if you have multiple cameras.

**Alarm never plays**
Check the console for `[Alarm] Warning: could not load 'assets/alarm.wav'`.
Make sure the file exists at that exact relative path and is a valid
`.wav`.

**LEFT or RIGHT doesn't seem to register**
Try `INVERT_HEAD_TURN = True` in `config.py` — this flips the detected
direction without touching any logic, useful if your camera's mirroring
doesn't match the assumed convention. If the *sensitivity* feels off
instead, adjust `HORIZONTAL_ENTER_THRESHOLD`/`_EXIT_THRESHOLD` slightly.

**Dashboard feels laggy**
Lower `GUI_TICK_MS` isn't the fix (it's already ~50Hz); check
`CAMERA_PUSH_FPS` and make sure nothing else on your machine is
competing for the webcam/CPU. Closing the optional `SHOW_CAMERA_PREVIEW`
window (if enabled) also frees up cycles.

**Recalibrating mid-session**
Currently calibration only runs once at startup. To recalibrate,
restart the app (`Ctrl+C` in the terminal, then `python main.py` again).

---

## 9. Extending

- **New alert states**: add a branch in `camera_worker.py`'s state logic,
  then add a matching entry to `_route_state()` and the `colors`/`labels`
  dicts in `dashboard.py`'s `_redraw_status()`.
- **Different actuator behavior**: all dashboard reaction rules live in
  `SafetyDashboard._route_state()` — it's the single place that maps
  driver state → `target_speed` / `hazard_active` / `brake_active` /
  `vibration_active`.
- **Real hardware integration** (e.g. CAN bus dispatch instead of a
  simulated dashboard): swap the body of `_redraw_car()` /
  `_redraw_steering()` for calls into your actuator interface, keeping
  the same `tick()` cadence.
