import cv2
import mediapipe as mp

# 初始化 MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=False,
                                   max_num_faces=1,
                                   refine_landmarks=True,  # 启用精细模型（嘴部效果更好）
                                   min_detection_confidence=0.5,
                                   min_tracking_confidence=0.5)

# 初始化绘图工具
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# 嘴部的关键点索引（基于官方468个点）
MOUTH_LANDMARKS = list(set([i for pair in mp_face_mesh.FACEMESH_LIPS for i in pair]))

# 打开摄像头
cap = cv2.VideoCapture(1)

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        print("读取视频帧失败")
        break

    # 转换颜色空间 BGR -> RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # 获取面部网格结果
    results = face_mesh.process(rgb_frame)

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            img_h, img_w, _ = frame.shape
            for idx in MOUTH_LANDMARKS:
                pt = face_landmarks.landmark[idx]
                x, y = int(pt.x * img_w), int(pt.y * img_h)
                cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)  # 在嘴部关键点画绿色小圆点

            # 如果你想画完整嘴部区域轮廓：
            mp_drawing.draw_landmarks(
                frame,
                face_landmarks,
                connections=mp_face_mesh.FACEMESH_LIPS,
                landmark_drawing_spec=None,
                connection_drawing_spec=mp_drawing.DrawingSpec(color=(0, 255, 255), thickness=1, circle_radius=1)
            )

    cv2.imshow('Mouth Tracking', frame)
    if cv2.waitKey(5) & 0xFF == 27:  # 按 Esc 退出
        break

cap.release()
cv2.destroyAllWindows()
