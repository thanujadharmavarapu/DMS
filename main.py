import cv2

import config
from detector import FaceDetector
from drowsiness import DrowsinessDetector
from head_pose import HeadPoseEstimator
from alert import Alarm
from utils import draw_circle, draw_status_panel


def run():

    cap = cv2.VideoCapture(config.CAMERA_INDEX)

    face_detector = FaceDetector()
    drowsiness_detector = DrowsinessDetector()
    head_pose_estimator = HeadPoseEstimator()
    alarm = Alarm(config.ALARM_SOUND)

    while True:

        success, frame = cap.read()

        if not success:
            break

        frame = cv2.flip(frame, 1)

        face = face_detector.detect_face(frame)

        # ------------------------------------------------------------
        # No face -> everything off, everything reset
        # ------------------------------------------------------------
        if face is None:

            alarm.stop()
            drowsiness_detector.reset()
            head_pose_estimator.reset()
            face_detector.reset()

            draw_status_panel(
                frame,
                [("NO FACE DETECTED", config.WARNING_COLOR)]
            )

            cv2.imshow(config.WINDOW_NAME, frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

            continue

        # ------------------------------------------------------------
        # Face present -> compute EAR
        # ------------------------------------------------------------
        left_eye, right_eye = face_detector.get_eye_points(face, frame)

        for point in left_eye:
            draw_circle(frame, point)
        for point in right_eye:
            draw_circle(frame, point)

        ear = drowsiness_detector.get_average_ear(left_eye, right_eye)

        # Head pose (yaw only matters -> LEFT/RIGHT/NORMAL)
        pose, _ = head_pose_estimator.estimate(face, frame)
        yaw = pose[1] if pose is not None else head_pose_estimator.baseline_yaw

        # ------------------------------------------------------------
        # Calibration phase (first ~3 seconds): look straight, eyes open
        # ------------------------------------------------------------
        if not drowsiness_detector.calibrated or not head_pose_estimator.calibrated:

            drowsiness_detector.calibrate(ear)
            head_pose_estimator.calibrate(yaw)

            draw_status_panel(
                frame,
                [
                    ("CALIBRATING...", config.TEXT_COLOR),
                    ("PLEASE LOOK STRAIGHT", config.TEXT_COLOR),
                    ("KEEP YOUR EYES OPEN", config.TEXT_COLOR),
                ]
            )

            cv2.imshow(config.WINDOW_NAME, frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

            continue

        # ------------------------------------------------------------
        # Normal monitoring (post-calibration)
        # ------------------------------------------------------------
        fatigue = drowsiness_detector.detect(ear)

        head_position = head_pose_estimator.get_head_position(yaw)
        look_away = head_pose_estimator.detect_look_away(head_position)

        # Single, non-overlapping driver state.
        # Fatigue (microsleep) takes priority since it is the more
        # immediately dangerous condition if both were ever true at once.
        if fatigue:
            status = "FATIGUE DETECTED"
            status_color = config.WARNING_COLOR
        elif look_away:
            status = "LOOK AWAY DETECTED"
            status_color = config.WARNING_COLOR
        else:
            status = "NORMAL"
            status_color = config.TEXT_COLOR

        # Alarm only during FATIGUE or LOOK AWAY
        if fatigue or look_away:
            alarm.start()
        else:
            alarm.stop()

        # ------------------------------------------------------------
        # Clean UI: EAR, Head Position, STATUS -- nothing else
        # ------------------------------------------------------------
        draw_status_panel(
            frame,
            [
                (f"EAR : {ear:.2f}", config.TEXT_COLOR),
                (f"Head Position : {head_position}", config.TEXT_COLOR),
                (f"STATUS : {status}", status_color),
            ]
        )

        cv2.imshow(config.WINDOW_NAME, frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    alarm.stop()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    run()
