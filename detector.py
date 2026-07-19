import cv2
import mediapipe as mp


class FaceDetector:

    def __init__(self):

        self.mp_face_mesh = mp.solutions.face_mesh

        self.face_mesh = self.mp_face_mesh.FaceMesh(

            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.75,
            min_tracking_confidence=0.75

        )

        # EAR Landmark Order
        self.LEFT_EYE = [
            33, 160, 158, 133, 153, 144
        ]

        self.RIGHT_EYE = [
            362, 385, 387, 263, 373, 380
        ]

        # Previous landmarks for smoothing
        self.prev_left = None
        self.prev_right = None

        # Lower smoothing = faster response
        self.SMOOTHING = 0.60

    # -------------------------------------

    def detect_face(self, frame):

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        results = self.face_mesh.process(rgb)

        if results.multi_face_landmarks:
            return results.multi_face_landmarks[0]

        return None

    # -------------------------------------

    def smooth_points(
        self,
        current_points,
        previous_points
    ):

        if previous_points is None:
            return current_points

        smooth = []

        for current, previous in zip(
            current_points,
            previous_points
        ):

            x = int(
                previous[0] * self.SMOOTHING +
                current[0] * (1 - self.SMOOTHING)
            )

            y = int(
                previous[1] * self.SMOOTHING +
                current[1] * (1 - self.SMOOTHING)
            )

            smooth.append((x, y))

        return smooth

    # -------------------------------------

    def get_eye_points(
        self,
        face_landmarks,
        frame
    ):

        h, w, _ = frame.shape

        left_eye = []
        right_eye = []

        for idx in self.LEFT_EYE:

            landmark = face_landmarks.landmark[idx]

            left_eye.append(

                (

                    int(landmark.x * w),

                    int(landmark.y * h)

                )

            )

        for idx in self.RIGHT_EYE:

            landmark = face_landmarks.landmark[idx]

            right_eye.append(

                (

                    int(landmark.x * w),

                    int(landmark.y * h)

                )

            )

        left_eye = self.smooth_points(
            left_eye,
            self.prev_left
        )

        right_eye = self.smooth_points(
            right_eye,
            self.prev_right
        )

        self.prev_left = left_eye
        self.prev_right = right_eye

        return left_eye, right_eye

    # -------------------------------------

    def reset(self):

        self.prev_left = None
        self.prev_right = None