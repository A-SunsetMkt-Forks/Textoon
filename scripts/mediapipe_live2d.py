import time
import random
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe import solutions
from mediapipe.framework.formats import landmark_pb2
import numpy as np
import cv2
import requests
import math

def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))

def rotation_matrix_to_angles(rotation_matrix):
    """
    Calculate Euler angles from rotation matrix.
    :param rotation_matrix: A 3*3 matrix with the following structure
    [Cosz*Cosy  Cosz*Siny*Sinx - Sinz*Cosx  Cosz*Siny*Cosx + Sinz*Sinx]
    [Sinz*Cosy  Sinz*Siny*Sinx + Sinz*Cosx  Sinz*Siny*Cosx - Cosz*Sinx]
    [  -Siny             CosySinx                   Cosy*Cosx         ]
    :return: Angles in degrees for each axis
    """
    x = math.atan2(rotation_matrix[2, 1], rotation_matrix[2, 2])
    y = math.atan2(-rotation_matrix[2, 0], math.sqrt(rotation_matrix[0, 0] ** 2 +
                                                     rotation_matrix[1, 0] ** 2))
    z = math.atan2(rotation_matrix[1, 0], rotation_matrix[0, 0])
    return np.array([x, y, z]) * 180. / math.pi

def draw_landmarks_on_image(rgb_image, detection_result):
    face_landmarks_list = detection_result.face_landmarks
    annotated_image = np.copy(rgb_image)

    # Loop through the detected faces to visualize.
    for idx in range(len(face_landmarks_list)):
        face_landmarks = face_landmarks_list[idx]

        # Draw the face landmarks.
        face_landmarks_proto = landmark_pb2.NormalizedLandmarkList()
        face_landmarks_proto.landmark.extend([
            landmark_pb2.NormalizedLandmark(x=landmark.x, y=landmark.y, z=landmark.z) for landmark in face_landmarks
        ])

        solutions.drawing_utils.draw_landmarks(
            image=annotated_image,
            landmark_list=face_landmarks_proto,
            connections=mp.solutions.face_mesh.FACEMESH_TESSELATION,
            landmark_drawing_spec=None,
            connection_drawing_spec=mp.solutions.drawing_styles
            .get_default_face_mesh_tesselation_style())
        solutions.drawing_utils.draw_landmarks(
            image=annotated_image,
            landmark_list=face_landmarks_proto,
            connections=mp.solutions.face_mesh.FACEMESH_CONTOURS,
            landmark_drawing_spec=None,
            connection_drawing_spec=mp.solutions.drawing_styles
            .get_default_face_mesh_contours_style())
        solutions.drawing_utils.draw_landmarks(
            image=annotated_image,
            landmark_list=face_landmarks_proto,
            connections=mp.solutions.face_mesh.FACEMESH_IRISES,
                landmark_drawing_spec=None,
                connection_drawing_spec=mp.solutions.drawing_styles
                .get_default_face_mesh_iris_connections_style())

    return annotated_image

def generate_data(url, vis=True):
    # Create an FaceLandmarker object.
    base_options = python.BaseOptions(model_asset_path='checkpoints/face_landmarker_v2_with_blendshapes.task')
    options = vision.FaceLandmarkerOptions(base_options=base_options,
                                        output_face_blendshapes=True,
                                        output_facial_transformation_matrixes=True,
                                        num_faces=1)
    detector = vision.FaceLandmarker.create_from_options(options)

    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(min_detection_confidence=0.5,
                                    min_tracking_confidence=0.5)

    # Open the video file
    cap = cv2.VideoCapture(0)
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Convert the frame to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        # Detect face landmarks from the input image.
        detection_result = detector.detect(image)
        # Head Pose Estimation
        mesh_results = face_mesh.process(frame_rgb)

        # print(f'detection_result: {detection_result}')
        if len(detection_result.face_blendshapes) > 0:
            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            # head estimation
            face_coordination_in_real_world = np.array([
                [285, 528, 200],
                [285, 371, 152],
                [197, 574, 128],
                [173, 425, 108],
                [360, 574, 128],
                [391, 425, 108]
            ], dtype=np.float64)

            h, w, _ = frame_bgr.shape
            face_coordination_in_image = []
            count_number = 0
            if mesh_results.multi_face_landmarks:
                face_landmarks = mesh_results.multi_face_landmarks[0]

                for idx, lm in enumerate(face_landmarks.landmark):
                    if idx in [1, 9, 57, 130, 287, 359]:
                        x, y = int(lm.x * w), int(lm.y * h)
                        face_coordination_in_image.append([x, y])

                face_coordination_in_image = np.array(face_coordination_in_image,
                                                    dtype=np.float64)

                # The camera matrix
                focal_length = 1 * w
                cam_matrix = np.array([[focal_length, 0, w / 2],
                                    [0, focal_length, h / 2],
                                    [0, 0, 1]])

                # The Distance Matrix
                dist_matrix = np.zeros((4, 1), dtype=np.float64)

                # Use solvePnP function to get rotation vector
                success, rotation_vec, transition_vec = cv2.solvePnP(
                    face_coordination_in_real_world, face_coordination_in_image,
                    cam_matrix, dist_matrix)

                # Use Rodrigues function to convert rotation vector to matrix
                rotation_matrix, jacobian = cv2.Rodrigues(rotation_vec)

                angle_result = rotation_matrix_to_angles(rotation_matrix)
                    
            if vis:
                annotated_image = draw_landmarks_on_image(image.numpy_view()[:,:,:3], detection_result)
                for i, info in enumerate(zip(('pitch', 'yaw', 'roll'), angle_result)):
                        k, v = info
                        text = f'{k}: {int(v)}'
                        cv2.putText(annotated_image, text, (20, i*30 + 20),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 0, 200), 2)
                cv2.imshow("Image", cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR))
                if cv2.waitKey(25) & 0xFF == ord('q'):
                    break
            
            # print(f"pitch Y: {angle_result[0]}, yaw X: {angle_result[1]}, roll Z: {angle_result[2]}")
            face_blendshapes = detection_result.face_blendshapes[0]
            face_blendshapes_scores = [face_blendshapes_category.score for face_blendshapes_category in face_blendshapes]

            model_payload = ['jawopen', 'mouthclose', 'mouthfunnel', 'mouthpucker', 'mouthstretchleft', 'mouthstretchright', 'mouthleft', 'mouthright', 'mouthsmile', 'mouthfrownleft', 'mouthfrownright', 'mouthshrugupper', 'mouthshruglower', 'mouthupperupleft', 'mouthupperupright', 'mouthlowerdownleft', 'mouthlowerdownright', 'mouthrollupper', 'mouthrolllower', 'mouthpressleft', 'mouthpressright', 'mouthcheekpuff', 'mouthdimpleleft', 'mouthdimpleright']
            live2d_bs_mapping_mediapipebs = {'jawopen': 25, 'mouthclose': 27, 'mouthfunnel': 32, 'mouthpucker': 38, 'mouthstretchleft': 46, 'mouthstretchright': 47, 'mouthleft': 33, 'mouthright': 39, 'mouthsmile': 44, 'mouthfrownleft': 30, 'mouthfrownright': 31, 'mouthshrugupper': 43, 'mouthshruglower': 42, 'mouthupperupleft': 48, 'mouthupperupright': 49, 'mouthlowerdownleft': 34, 'mouthlowerdownright': 35, 'mouthrollupper': 41, 'mouthrolllower': 40, 'mouthpressleft': 36, 'mouthpressright': 37, 'mouthcheekpuff': 6, 'mouthdimpleleft': 28, 'mouthdimpleright': 29}
            payload = dict()
            for bs_name in model_payload:
                payload[bs_name] = float(face_blendshapes_scores[live2d_bs_mapping_mediapipebs[bs_name]])
            payload['headx'] = clamp(angle_result[1], -30, 30)
            payload['heady'] = clamp(angle_result[0], -30, 30)
            payload['headz'] = clamp(angle_result[2], -30, 30)
            print(f'jawopen: {payload["jawopen"]}, X: {payload["headx"]}, Y: {payload["heady"]}, Z: {payload["headz"]}')
            # 发送HTTP POST请求
            try:
                response = requests.post(url, json=payload)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                print(f"Error sending data to server: {e}")
            
        else:
            cv2.imshow("Image", frame)
            if cv2.waitKey(25) & 0xFF == ord('q'):
                break
    
if __name__ == "__main__":
    FLASK_SERVER_URL = 'http://0.0.0.0:4800/api/send_mouth_y'
    generate_data(FLASK_SERVER_URL)