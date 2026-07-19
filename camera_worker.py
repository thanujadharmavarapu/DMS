"""
camera_worker.py
----------------
Background worker thread that owns the webcam and the MediaPipe / EAR /
head-pose pipeline. It NEVER touches Tkinter. It only computes state and
pushes small dict snapshots into a `queue.Queue`, which the GUI thread
drains on its own schedule (see dashboard.py -> tick()).

This is the classic producer/consumer split that keeps a Tkinter mainloop
from freezing: heavy CV work happens here, off the GUI thread, at whatever
rate the camera can sustain, and the GUI just reads the latest snapshot.
"""

import queue
import time

import cv2

import config
from detector import FaceDetector
from drowsiness import DrowsinessDetector
from head_pose import HeadPoseEstimator


class CameraWorker:
    """
    Runs the full CV pipeline in its own thread and reports driver state
    ("CALIBRATING", "NO_FACE", "NORMAL", "DISTRACTED", "FATIGUE") to a
    queue.Queue as {'state', 'ear', 'head_position', 'timestamp'} dicts.

    Usage:
        data_queue = queue.Queue(maxsize=config.QUEUE_MAXSIZE)
        stop_event = threading.Event()
        worker = CameraWorker(data_queue, stop_event)
        thread = threading.Thread(target=worker.run, daemon=True)
        thread.start()
        ...
        stop_event.set()
        thread.join(timeout=2.0)
    """

    def __init__(self, data_queue: "queue.Queue", stop_event):
        self.queue = data_queue
        self.stop_event = stop_event
        self.cap = None

    # ------------------------------------------------------------

    def _push(self, state, ear, head_position):
        """Thread-safe, non-blocking push. Drops the oldest frame if the
        queue is momentarily full so the GUI never blocks on a stale read."""
        payload = {
            "state": state,
            "ear": ear,
            "head_position": head_position,
            "timestamp": time.time(),
        }
        try:
            self.queue.put_nowait(payload)
        except queue.Full:
            try:
                self.queue.get_nowait()   # drop oldest
            except queue.Empty:
                pass
            try:
                self.queue.put_nowait(payload)
            except queue.Full:
                pass  # extremely unlikely; just skip this frame

    # ------------------------------------------------------------

    def run(self):
        """Main loop for the background thread. Call this via
        threading.Thread(target=worker.run, daemon=True)."""

        self.cap = cv2.VideoCapture(config.CAMERA_INDEX)

        face_detector = FaceDetector()
        drowsiness_detector = DrowsinessDetector()
        head_pose_estimator = HeadPoseEstimator()

        push_interval = 1.0 / config.CAMERA_PUSH_FPS
        last_push = 0.0

        try:
            while not self.stop_event.is_set():

                success, frame = self.cap.read()
                if not success:
                    # Camera hiccup / disconnect -> report NO_FACE, keep trying
                    self._push("NO_FACE", 0.0, "NORMAL")
                    time.sleep(0.05)
                    continue

                frame = cv2.flip(frame, 1)

                face = face_detector.detect_face(frame)

                if face is None:
                    drowsiness_detector.reset()
                    head_pose_estimator.reset()
                    face_detector.reset()
                    state, ear, head_position = "NO_FACE", 0.0, "NORMAL"

                else:
                    left_eye, right_eye = face_detector.get_eye_points(face, frame)
                    ear = drowsiness_detector.get_average_ear(left_eye, right_eye)

                    ratio = head_pose_estimator.compute_horizontal_ratio(face, frame)

                    if not drowsiness_detector.calibrated or not head_pose_estimator.calibrated:
                        drowsiness_detector.calibrate(ear)
                        head_pose_estimator.calibrate(ratio)
                        state, head_position = "CALIBRATING", "NORMAL"

                    else:
                        fatigue = drowsiness_detector.detect(ear)
                        head_position = head_pose_estimator.get_head_position(ratio)
                        look_away = head_pose_estimator.detect_look_away(head_position)

                        if fatigue:
                            state = "FATIGUE"
                        elif look_away:
                            state = "DISTRACTED"
                        else:
                            state = "NORMAL"

                if config.SHOW_CAMERA_PREVIEW:
                    cv2.putText(frame, f"{state} | EAR {ear:.2f}", (20, 40),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    cv2.imshow(config.WINDOW_NAME, frame)
                    cv2.waitKey(1)

                now = time.time()
                if now - last_push >= push_interval:
                    self._push(state, ear, head_position)
                    last_push = now

        finally:
            if self.cap is not None:
                self.cap.release()
            if config.SHOW_CAMERA_PREVIEW:
                cv2.destroyAllWindows()