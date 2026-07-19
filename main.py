import cv2

from detector import FaceDetector
from drowsiness import DrowsinessDetector
from utils import draw_circle, draw_text


cap = cv2.VideoCapture(0)


face_detector = FaceDetector()
drowsiness_detector = DrowsinessDetector()


while True:

    success, frame = cap.read()

    if not success:
        break


    frame = cv2.flip(frame, 1)


    face = face_detector.detect_face(frame)


    if face:

        left_eye, right_eye = face_detector.get_eye_points(
            face,
            frame
        )


        for point in left_eye:
            draw_circle(frame, point)


        for point in right_eye:
            draw_circle(frame, point)


        ear = drowsiness_detector.get_average_ear(
            left_eye,
            right_eye
        )


        drowsy = drowsiness_detector.detect(ear)


        draw_text(
            frame,
            f"EAR: {ear:.3f}",
            (20, 40)
        )


        if drowsy:

            draw_text(
                frame,
                "DROWSINESS DETECTED!",
                (20, 80),
                (0,0,255)
            )

        else:

            draw_text(
                frame,
                "DRIVER ALERT",
                (20,80),
                (0,255,0)
            )


    else:

        draw_text(
            frame,
            "NO FACE DETECTED",
            (20,40),
            (0,0,255)
        )


    cv2.imshow(
        "Driver Monitoring System",
        frame
    )


    if cv2.waitKey(1) & 0xFF == ord("q"):
        break



cap.release()
cv2.destroyAllWindows()