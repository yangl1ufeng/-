import cv2
import mediapipe as mp
import numpy as np
import threading

# 初始化 MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=False,
                                   max_num_faces=1,
                                   refine_landmarks=True,
                                   min_detection_confidence=0.5,
                                   min_tracking_confidence=0.5)

# 初始化绘图工具
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# 嘴部的关键点索引（基于官方468个点）
MOUTH_LANDMARKS = list(set([i for pair in mp_face_mesh.FACEMESH_LIPS for i in pair]))

# 创建全局容器存储嘴部特征点和中心点坐标
mouth_data = {
    "center": (0, 0),           # 嘴部中心点
    "points": [],               # 所有嘴部特征点
    "frame_count": 0,           # 帧计数
    "is_detected": False,       # 是否检测到嘴部
    "last_update_time": 0       # 最后更新时间
}

# 添加线程锁以确保数据安全
data_lock = threading.Lock()

# 获取当前嘴部数据的函数（可从其他模块调用）
def get_mouth_data():
    with data_lock:
        return mouth_data.copy()

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

    # 更新检测状态
    with data_lock:
        mouth_data["is_detected"] = False
        mouth_data["frame_count"] += 1
        
    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            img_h, img_w, _ = frame.shape
            
            # 收集所有嘴部关键点的坐标
            mouth_points = []
            for idx in MOUTH_LANDMARKS:
                pt = face_landmarks.landmark[idx]
                x, y = int(pt.x * img_w), int(pt.y * img_h)
                mouth_points.append((x, y))
                cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)  # 在嘴部关键点画绿色小圆点
            
            # 计算嘴部中心点
            if mouth_points:
                mouth_points_array = np.array(mouth_points)
                mouth_center_x = int(np.mean(mouth_points_array[:, 0]))
                mouth_center_y = int(np.mean(mouth_points_array[:, 1]))
                
                # 标记嘴部中心点（红色）
                cv2.circle(frame, (mouth_center_x, mouth_center_y), 5, (0, 0, 255), -1)
                
                # 显示中心点坐标
                cv2.putText(frame, f"Center: ({mouth_center_x}, {mouth_center_y})", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                # 更新全局数据容器
                with data_lock:
                    mouth_data["center"] = (mouth_center_x, mouth_center_y)
                    mouth_data["points"] = mouth_points.copy()  # 使用copy以避免引用问题
                    mouth_data["is_detected"] = True
                    mouth_data["last_update_time"] = cv2.getTickCount() / cv2.getTickFrequency()
                
                # 显示检测到的点数
                cv2.putText(frame, f"Points: {len(mouth_points)}", 
                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # 画完整嘴部区域轮廓
            mp_drawing.draw_landmarks(
                frame,
                face_landmarks,
                connections=mp_face_mesh.FACEMESH_LIPS,
                landmark_drawing_spec=None,
                connection_drawing_spec=mp_drawing.DrawingSpec(color=(0, 255, 255), thickness=1, circle_radius=1)
            )

    # 显示检测状态
    status = "Detected" if mouth_data["is_detected"] else "Not Detected"
    cv2.putText(frame, f"Status: {status}", 
               (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

    cv2.imshow('Mouth Tracking', frame)
    if cv2.waitKey(5) & 0xFF == 27:  # 按 Esc 退出
        break

cap.release()
cv2.destroyAllWindows()

# 示例：如何在其他地方使用这些数据
# current_mouth_data = get_mouth_data()
# if current_mouth_data["is_detected"]:
#     center = current_mouth_data["center"]
#     points = current_mouth_data["points"]
#     # 进行其他处理...
