"""
main.py
-------
Entry point that wires together:
  - CameraWorker  (background thread: cv2 + MediaPipe + EAR/head-pose)
  - queue.Queue   (thread-safe hand-off, camera -> GUI)
  - SafetyDashboard (Tkinter mainloop, main thread only)
  - Alarm         (audio cue, triggered from the main thread)

This is the only place that starts/stops the thread, so shutdown is
centralized and safe: closing the window sets a threading.Event, the
camera thread notices it on its next loop iteration and releases the
webcam, and only then does the Tk root get destroyed.
"""

import queue
import threading
import tkinter as tk

import config
from alert import Alarm
from camera_worker import CameraWorker
from dashboard import SafetyDashboard


class App:

    def __init__(self):
        self.data_queue = queue.Queue(maxsize=config.QUEUE_MAXSIZE)
        self.stop_event = threading.Event()

        self.alarm = Alarm(config.ALARM_SOUND)

        self.worker = CameraWorker(self.data_queue, self.stop_event)
        self.camera_thread = threading.Thread(
            target=self.worker.run,
            name="CameraWorkerThread",
            daemon=True,   # safety net: won't block interpreter exit even
                           # if graceful shutdown is somehow skipped
        )

        self.root = tk.Tk()
        self.dashboard = SafetyDashboard(
            self.root,
            self.data_queue,
            on_close_callback=self.shutdown,
        )

        # Drive the alarm from the dashboard's live state, on the main
        # thread, right after each GUI tick -- avoids any cross-thread
        # audio calls while still reacting within ~20ms of a state change.
        self._hook_alarm_to_dashboard()

    # ------------------------------------------------------------

    def _hook_alarm_to_dashboard(self):
        original_tick = self.dashboard.tick

        def tick_with_alarm():
            original_tick()
            if self.dashboard.state in ("FATIGUE", "DISTRACTED"):
                self.alarm.start()
            else:
                self.alarm.stop()

        self.dashboard.tick = tick_with_alarm

    # ------------------------------------------------------------

    def run(self):
        self.camera_thread.start()
        self.root.mainloop()

    # ------------------------------------------------------------

    def shutdown(self):
        """Called once, from the Tk WM_DELETE_WINDOW handler."""
        self.stop_event.set()
        self.alarm.stop()

        # Give the camera thread a moment to notice the stop flag,
        # finish its current frame, and release cv2.VideoCapture.
        self.camera_thread.join(timeout=2.0)

        self.root.destroy()


if __name__ == "__main__":
    App().run()
