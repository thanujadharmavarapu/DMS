import cv2
import numpy as np


class HeadPoseEstimator:

    def __init__(self):

        # 3D Face Model
        self.model_points = np.array([

            (0.0, 0.0, 0.0),          # Nose

            (0.0, -63.6, -12.5),      # Chin

            (-43.3, 32.7, -26.0),     # Left Eye

            (43.3, 32.7, -26.0),      # Right Eye

            (-28.9, -28.9, -24.1),    # Left Mouth

            (28.9, -28.9, -24.1)      # Right Mouth

        ], dtype=np.float64)

        # MediaPipe Landmark IDs
        self.landmark_ids = [
            1,
            152,
            33,
            263,
            61,
            291
        ]

        # Yaw smoothing
        self.previous_yaw = None
        self.SMOOTHING = 0.60

    # ------------------------------------------

    def estimate(
        self,
        face_landmarks,
        frame
    ):

        h, w, _ = frame.shape

        image_points = []

        for idx in self.landmark_ids:

            landmark = face_landmarks.landmark[idx]

            image_points.append(

                (

                    int(landmark.x * w),

                    int(landmark.y * h)

                )

            )

        image_points = np.array(
            image_points,
            dtype=np.float64
        )

        focal_length = w

        camera_matrix = np.array([

            [focal_length, 0, w / 2],

            [0, focal_length, h / 2],

            [0, 0, 1]

        ], dtype=np.float64)

        dist_coeffs = np.zeros((4, 1))

        success, rotation_vector, translation_vector = cv2.solvePnP(

            self.model_points,

            image_points,

            camera_matrix,

            dist_coeffs,

            flags=cv2.SOLVEPNP_ITERATIVE

        )

        if not success:

            return None, image_points

        rotation_matrix, _ = cv2.Rodrigues(
            rotation_vector
        )

        angles, _, _, _, _, _ = cv2.RQDecomp3x3(
            rotation_matrix
        )

        pitch = angles[0]
        yaw = angles[1]
        roll = angles[2]

        # -------------------------
        # Smooth only yaw
        # -------------------------

        if self.previous_yaw is None:

            self.previous_yaw = yaw

        yaw = (

            self.SMOOTHING * self.previous_yaw +

            (1 - self.SMOOTHING) * yaw

        )

        self.previous_yaw = yaw

        return (

            pitch,

            yaw,

            roll

        ), image_points

    # ------------------------------------------

    def reset(self):

        self.previous_yaw = None