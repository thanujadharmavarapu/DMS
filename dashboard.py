"""
dashboard.py
------------
Dark-mode automotive telematics dashboard, built on Tkinter Canvas.

This ONLY runs on the main thread (Tkinter is not thread-safe). It never
talks to the camera or MediaPipe directly. Instead it polls a queue.Queue
on a `root.after(config.GUI_TICK_MS, tick)` cadence, drains it down to the
freshest snapshot, and drives all animation (speed easing, AEB braking,
hazard blink, steering-wheel vibration + ripple waves) from that state.
"""

import math
import queue
import time
import tkinter as tk

import config


class SafetyDashboard:

    def __init__(self, root: tk.Tk, data_queue: "queue.Queue", on_close_callback):
        self.root = root
        self.queue = data_queue
        self.on_close_callback = on_close_callback

        # ---- Live state coming from the camera thread ----
        self.state = "CALIBRATING"
        self.ear = 0.0
        self.head_position = "NORMAL"
        self.last_update = time.time()

        # ---- Animated / derived values ----
        self.current_speed = 0.0
        self.target_speed = 0.0
        self.hazard_active = False        # should hazards be flashing at all
        self.hazard_visible = False        # current blink phase (on/off)
        self._last_hazard_toggle = time.time()
        self.brake_active = False
        self.vibration_active = False
        self.vibration_phase = 0.0
        self.waves = []  # list of current ripple radii

        self._build_window()
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._handle_close)

        self.tick()

    # ==================================================================
    # WINDOW / STATIC LAYOUT
    # ==================================================================

    def _build_window(self):
        self.root.title(config.DASH_WINDOW_TITLE)
        self.root.geometry(f"{config.DASH_WIDTH}x{config.DASH_HEIGHT}")
        self.root.configure(bg=config.BG_DARK)
        self.root.resizable(False, False)

    def _build_ui(self):
        self.canvas = tk.Canvas(
            self.root,
            width=config.DASH_WIDTH,
            height=config.DASH_HEIGHT,
            bg=config.BG_DARK,
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self._draw_header()
        self._draw_car_panel()
        self._draw_steering_panel()
        self._draw_speed_gauge()
        self._draw_status_panel()

    # ------------------------------------------------------------
    def _draw_header(self):
        self.canvas.create_text(
            20, 20, anchor="nw",
            text="ADVANCED SAFETY DASHBOARD",
            fill=config.TEXT_LIGHT,
            font=("Consolas", 18, "bold"),
        )
        self.canvas.create_text(
            20, 48, anchor="nw",
            text="Real-Time Driver Monitoring · Edge AI",
            fill=config.TEXT_DIM,
            font=("Consolas", 11),
        )
        self.canvas.create_line(
            20, 75, config.DASH_WIDTH - 20, 75,
            fill=config.GRID_LINE, width=1,
        )

    # ------------------------------------------------------------
    # TOP-DOWN CAR + HAZARDS + BRAKE LAMPS
    # ------------------------------------------------------------
    def _draw_car_panel(self):
        # Panel background
        self.canvas.create_rectangle(
            20, 95, 480, 620,
            fill=config.PANEL_DARK, outline=config.GRID_LINE
        )
        self.canvas.create_text(
            40, 110, anchor="nw", text="VEHICLE STATUS",
            fill=config.TEXT_DIM, font=("Consolas", 10, "bold")
        )

        cx = 250
        top, bottom = 160, 560
        half_w = 70

        # Car body (top-down)
        self.car_body = self.canvas.create_rectangle(
            cx - half_w, top, cx + half_w, bottom,
            fill=config.CAR_BODY_COLOR, outline=config.GRID_LINE, width=2,
        )
        # Windshield
        self.canvas.create_rectangle(
            cx - 45, top + 30, cx + 45, top + 90,
            fill=config.BG_DARK, outline=config.GRID_LINE,
        )
        # Rear window
        self.canvas.create_rectangle(
            cx - 45, bottom - 90, cx + 45, bottom - 40,
            fill=config.BG_DARK, outline=config.GRID_LINE,
        )

        # Wheels
        wheel_w, wheel_h = 18, 50
        wheel_positions = [
            (cx - half_w - wheel_w / 2, top + 40),
            (cx + half_w - wheel_w / 2, top + 40),
            (cx - half_w - wheel_w / 2, bottom - 40 - wheel_h),
            (cx + half_w - wheel_w / 2, bottom - 40 - wheel_h),
        ]
        for wx, wy in wheel_positions:
            self.canvas.create_rectangle(
                wx, wy, wx + wheel_w, wy + wheel_h,
                fill=config.WHEEL_COLOR, outline=config.GRID_LINE,
            )

        # Headlights (front, static white)
        r = 6
        self.canvas.create_oval(cx - half_w + 6 - r, top + 6 - r,
                                 cx - half_w + 6 + r, top + 6 + r,
                                 fill="#dfe6f0", outline="")
        self.canvas.create_oval(cx + half_w - 6 - r, top + 6 - r,
                                 cx + half_w - 6 + r, top + 6 + r,
                                 fill="#dfe6f0", outline="")

        # Hazard lights: 4 amber indicators, one at each corner
        hazard_r = 7
        hazard_coords = [
            (cx - half_w + 6, top + 6),
            (cx + half_w - 6, top + 6),
            (cx - half_w + 6, bottom - 6),
            (cx + half_w - 6, bottom - 6),
        ]
        self.hazard_ids = []
        for hx, hy in hazard_coords:
            item = self.canvas.create_oval(
                hx - hazard_r, hy - hazard_r, hx + hazard_r, hy + hazard_r,
                fill=config.PANEL_DARK, outline=config.GRID_LINE, width=1,
            )
            self.hazard_ids.append(item)

        # Brake lamps: rear light bar
        self.brake_lamp = self.canvas.create_rectangle(
            cx - 50, bottom - 12, cx + 50, bottom - 2,
            fill=config.PANEL_DARK, outline=config.GRID_LINE,
        )

        self.aeb_text = self.canvas.create_text(
            cx, bottom + 20, text="AEB: STANDBY",
            fill=config.TEXT_DIM, font=("Consolas", 11, "bold"),
        )

    # ------------------------------------------------------------
    # STEERING WHEEL (vibration + cyan ripple waves)
    # ------------------------------------------------------------
    def _draw_steering_panel(self):
        self.canvas.create_rectangle(
            500, 95, 980, 360,
            fill=config.PANEL_DARK, outline=config.GRID_LINE
        )
        self.canvas.create_text(
            520, 110, anchor="nw", text="STEERING INPUT",
            fill=config.TEXT_DIM, font=("Consolas", 10, "bold")
        )

        self.wheel_cx, self.wheel_cy = 740, 240
        self.wheel_r = 75

        # Ripple wave placeholders (created/destroyed dynamically)
        self.wave_ids = []

        self.wheel_ring = self.canvas.create_oval(
            self.wheel_cx - self.wheel_r, self.wheel_cy - self.wheel_r,
            self.wheel_cx + self.wheel_r, self.wheel_cy + self.wheel_r,
            outline=config.TEXT_DIM, width=6,
        )
        self.wheel_spokes = []
        for angle_deg in (90, 210, 330):
            rad = math.radians(angle_deg)
            x = self.wheel_cx + self.wheel_r * math.cos(rad)
            y = self.wheel_cy - self.wheel_r * math.sin(rad)
            spoke = self.canvas.create_line(
                self.wheel_cx, self.wheel_cy, x, y,
                fill=config.TEXT_DIM, width=6,
            )
            self.wheel_spokes.append(spoke)
        self.wheel_hub = self.canvas.create_oval(
            self.wheel_cx - 14, self.wheel_cy - 14,
            self.wheel_cx + 14, self.wheel_cy + 14,
            fill=config.PANEL_DARK, outline=config.TEXT_DIM, width=3,
        )

        self.vibration_label = self.canvas.create_text(
            self.wheel_cx, 335, text="STEERING: STEADY",
            fill=config.TEXT_DIM, font=("Consolas", 11, "bold"),
        )

    # ------------------------------------------------------------
    # SPEED GAUGE
    # ------------------------------------------------------------
    def _draw_speed_gauge(self):
        self.canvas.create_rectangle(
            500, 380, 980, 560,
            fill=config.PANEL_DARK, outline=config.GRID_LINE
        )
        self.canvas.create_text(
            520, 395, anchor="nw", text="SPEED",
            fill=config.TEXT_DIM, font=("Consolas", 10, "bold")
        )

        self.gauge_cx, self.gauge_cy, self.gauge_r = 740, 520, 85

        self.canvas.create_arc(
            self.gauge_cx - self.gauge_r, self.gauge_cy - self.gauge_r,
            self.gauge_cx + self.gauge_r, self.gauge_cy + self.gauge_r,
            start=0, extent=180, style="arc",
            outline=config.GRID_LINE, width=10,
        )

        self.gauge_needle = self.canvas.create_line(
            self.gauge_cx, self.gauge_cy, self.gauge_cx, self.gauge_cy - self.gauge_r,
            fill=config.ACCENT_GREEN, width=4,
        )
        self.gauge_hub = self.canvas.create_oval(
            self.gauge_cx - 6, self.gauge_cy - 6, self.gauge_cx + 6, self.gauge_cy + 6,
            fill=config.TEXT_LIGHT, outline="",
        )

        self.speed_text = self.canvas.create_text(
            self.gauge_cx, self.gauge_cy + 35, text=f"0 {config.SPEED_UNIT}",
            fill=config.TEXT_LIGHT, font=("Consolas", 20, "bold"),
        )

    # ------------------------------------------------------------
    # STATUS PANEL (EAR / head position / driver state)
    # ------------------------------------------------------------
    def _draw_status_panel(self):
        self.status_text = self.canvas.create_text(
            250, 640, text="STATUS: CALIBRATING",
            fill=config.TEXT_LIGHT, font=("Consolas", 13, "bold"),
        )
        self.ear_text = self.canvas.create_text(
            740, 590, text="EAR: --   |   HEAD: --",
            fill=config.TEXT_DIM, font=("Consolas", 11),
        )

    # ==================================================================
    # QUEUE DRAIN + STATE ROUTING
    # ==================================================================

    def _drain_queue(self):
        """Pull every pending message and keep only the freshest one -- the
        GUI never needs stale frames, just the current driver state."""
        latest = None
        try:
            while True:
                latest = self.queue.get_nowait()
        except queue.Empty:
            pass

        if latest is not None:
            self.state = latest["state"]
            self.ear = latest["ear"]
            self.head_position = latest["head_position"]
            self.last_update = latest["timestamp"]

    def _route_state(self):
        """Translate the current driver state into dashboard mechanics."""

        if self.state == "NORMAL":
            self.target_speed = config.MAX_SPEED
            self.hazard_active = False
            self.brake_active = False
            self.vibration_active = False

        elif self.state == "DISTRACTED":
            # Keep cruising, just alert via steering wheel vibration + waves
            self.target_speed = config.MAX_SPEED
            self.hazard_active = False
            self.brake_active = False
            self.vibration_active = True

        elif self.state == "FATIGUE":
            # Automatic Emergency Braking sequence
            self.target_speed = 0.0
            self.hazard_active = True
            self.brake_active = True
            self.vibration_active = True

        elif self.state == "NO_FACE":
            # Driver not visible to the system -> treat as a precaution:
            # slow down and flash hazards, but no steering-vibration cue
            # since we can't say the driver is distracted specifically.
            self.target_speed = 0.0
            self.hazard_active = True
            self.brake_active = True
            self.vibration_active = False

        else:  # "CALIBRATING" or unknown
            self.target_speed = 0.0
            self.hazard_active = False
            self.brake_active = False
            self.vibration_active = False

    # ==================================================================
    # ANIMATION
    # ==================================================================

    def _animate_speed(self):
        """
        Rate-based motion: the speed changes by a fixed km/h-per-second
        amount each tick, rather than a percentage of the remaining gap.
        This is what makes AEB braking feel like genuine gradual braking
        (a straight, controlled ramp down to 0) instead of a sudden snap
        that overshoots-then-crawls like exponential easing would.
        """
        dt = config.GUI_TICK_MS / 1000.0
        rate = config.AEB_DECEL_RATE if self.brake_active else config.ACCEL_RATE
        max_step = rate * dt

        delta = self.target_speed - self.current_speed
        if abs(delta) <= max_step:
            self.current_speed = self.target_speed
        else:
            self.current_speed += max_step if delta > 0 else -max_step

    def _animate_hazards(self):
        now = time.time()
        if not self.hazard_active:
            self.hazard_visible = False
            return
        if (now - self._last_hazard_toggle) * 1000 >= config.HAZARD_BLINK_MS:
            self.hazard_visible = not self.hazard_visible
            self._last_hazard_toggle = now

    def _animate_vibration(self):
        if self.vibration_active:
            self.vibration_phase += config.VIBRATION_SPEED
            # Spawn a fresh ripple wave periodically
            if len(self.waves) == 0 or self.waves[-1] > 18:
                self.waves.append(0)
        else:
            self.vibration_phase = 0.0

        # Grow existing waves, drop ones that exceed max radius
        self.waves = [w + config.WAVE_GROWTH for w in self.waves]
        self.waves = [w for w in self.waves if w <= config.WAVE_MAX_RADIUS]

    # ==================================================================
    # DRAW (apply animated state to canvas items)
    # ==================================================================

    def _redraw_car(self):
        color = config.ACCENT_AMBER if (self.hazard_active and self.hazard_visible) else config.PANEL_DARK
        for item in self.hazard_ids:
            self.canvas.itemconfig(item, fill=color)

        brake_color = config.ACCENT_RED if self.brake_active else config.PANEL_DARK
        self.canvas.itemconfig(self.brake_lamp, fill=brake_color)

        aeb_msg = "AEB: GRADUAL BRAKING" if self.brake_active else "AEB: STANDBY"
        aeb_color = config.ACCENT_RED if self.brake_active else config.TEXT_DIM
        self.canvas.itemconfig(self.aeb_text, text=aeb_msg, fill=aeb_color)

    def _redraw_steering(self):
        # Clear old ripple graphics, redraw current ones
        for item in self.wave_ids:
            self.canvas.delete(item)
        self.wave_ids = []

        if self.vibration_active:
            for radius in self.waves:
                item = self.canvas.create_oval(
                    self.wheel_cx - radius, self.wheel_cy - radius,
                    self.wheel_cx + radius, self.wheel_cy + radius,
                    outline=config.ACCENT_CYAN, width=2,
                )
                self.wave_ids.append(item)

            offset_x = math.sin(self.vibration_phase) * config.VIBRATION_AMPLITUDE
            offset_y = math.cos(self.vibration_phase * 1.3) * config.VIBRATION_AMPLITUDE
            wheel_color = config.ACCENT_CYAN
            label_text, label_color = "STEERING: VIBRATING", config.ACCENT_CYAN
        else:
            offset_x = offset_y = 0
            wheel_color = config.TEXT_DIM
            label_text, label_color = "STEERING: STEADY", config.TEXT_DIM

        self.canvas.coords(
            self.wheel_ring,
            self.wheel_cx - self.wheel_r + offset_x, self.wheel_cy - self.wheel_r + offset_y,
            self.wheel_cx + self.wheel_r + offset_x, self.wheel_cy + self.wheel_r + offset_y,
        )
        self.canvas.itemconfig(self.wheel_ring, outline=wheel_color)

        for i, angle_deg in enumerate((90, 210, 330)):
            rad = math.radians(angle_deg)
            x = self.wheel_cx + offset_x + self.wheel_r * math.cos(rad)
            y = self.wheel_cy + offset_y - self.wheel_r * math.sin(rad)
            self.canvas.coords(self.wheel_spokes[i], self.wheel_cx + offset_x, self.wheel_cy + offset_y, x, y)
            self.canvas.itemconfig(self.wheel_spokes[i], fill=wheel_color)

        self.canvas.coords(
            self.wheel_hub,
            self.wheel_cx - 14 + offset_x, self.wheel_cy - 14 + offset_y,
            self.wheel_cx + 14 + offset_x, self.wheel_cy + 14 + offset_y,
        )
        self.canvas.itemconfig(self.wheel_hub, outline=wheel_color)
        self.canvas.itemconfig(self.vibration_label, text=label_text, fill=label_color)

        # Keep ripples visually behind the wheel graphics
        for item in self.wave_ids:
            self.canvas.tag_lower(item, self.wheel_ring)

    def _redraw_gauge(self):
        angle_deg = 180 - (self.current_speed / config.MAX_SPEED) * 180
        rad = math.radians(angle_deg)
        x = self.gauge_cx + self.gauge_r * math.cos(rad)
        y = self.gauge_cy - self.gauge_r * math.sin(rad)
        self.canvas.coords(self.gauge_needle, self.gauge_cx, self.gauge_cy, x, y)

        if self.current_speed >= config.MAX_SPEED - 5:
            needle_color = config.ACCENT_GREEN
        elif self.brake_active:
            needle_color = config.ACCENT_RED
        else:
            needle_color = config.ACCENT_CYAN
        self.canvas.itemconfig(self.gauge_needle, fill=needle_color)

        self.canvas.itemconfig(self.speed_text, text=f"{self.current_speed:0.0f} {config.SPEED_UNIT}")

    def _redraw_status(self):
        colors = {
            "NORMAL": config.ACCENT_GREEN,
            "DISTRACTED": config.ACCENT_CYAN,
            "FATIGUE": config.ACCENT_RED,
            "NO_FACE": config.ACCENT_AMBER,
            "CALIBRATING": config.TEXT_DIM,
        }
        labels = {
            "NORMAL": "STATUS: NORMAL",
            "DISTRACTED": "STATUS: LOOK AWAY DETECTED",
            "FATIGUE": "STATUS: FATIGUE DETECTED",
            "NO_FACE": "STATUS: NO FACE DETECTED",
            "CALIBRATING": "STATUS: CALIBRATING...",
        }
        color = colors.get(self.state, config.TEXT_DIM)
        text = labels.get(self.state, f"STATUS: {self.state}")

        self.canvas.itemconfig(self.status_text, text=text, fill=color)
        self.canvas.itemconfig(
            self.ear_text,
            text=f"EAR: {self.ear:0.2f}   |   HEAD: {self.head_position}",
        )

    # ==================================================================
    # MAIN TICK -- the ONLY place the queue is touched from the GUI side
    # ==================================================================

    def tick(self):
        self._drain_queue()
        self._route_state()

        self._animate_speed()
        self._animate_hazards()
        self._animate_vibration()

        self._redraw_car()
        self._redraw_steering()
        self._redraw_gauge()
        self._redraw_status()

        self.root.after(config.GUI_TICK_MS, self.tick)

    # ==================================================================
    # SHUTDOWN
    # ==================================================================

    def _handle_close(self):
        self.on_close_callback()