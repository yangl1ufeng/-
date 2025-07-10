import cv2
import numpy as np
import serial
import time
import threading
import mediapipe as mp

# 串口配置
SERIAL_PORT = 'COM5'  # 替换成你的USB虚拟串口号
BAUDRATE = 115200
TIMEOUT = 1

# 定义嘴部坐标到舵机角度的映射参数
# 假设摄像头分辨率为640x480
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# 舵机限制
SERVO_X_MIN = 0    # 水平舵机最小角度
SERVO_X_MAX = 180  # 水平舵机最大角度
SERVO_Y_MIN = 0    # 垂直舵机最小角度
SERVO_Y_MAX = 180  # 垂直舵机最大角度

# 定义舵机编号
SERVO_X_ID = 1  # 水平方向舵机ID
SERVO_Y_ID = 2  # 垂直方向舵机ID

# 嘴部区域限制
MOUTH_X_MIN = 100  # 可检测嘴部最左位置
MOUTH_X_MAX = 540  # 可检测嘴部最右位置
MOUTH_Y_MIN = 100  # 可检测嘴部最上位置
MOUTH_Y_MAX = 380  # 可检测嘴部最下位置

# 坐标到角度的映射函数
def map_coordinate_to_angle(coord, coord_min, coord_max, angle_min, angle_max):
    """将坐标值映射到舵机角度"""
    # 边界检查
    coord = max(coord_min, min(coord, coord_max))
    # 线性映射
    angle = angle_min + (coord - coord_min) * (angle_max - angle_min) / (coord_max - coord_min)
    return int(angle)

# 发送舵机控制命令
def set_servo_angle(ser, servo_id, angle):
    """发送舵机角度命令"""
    cmd = f"set_servo_angle {servo_id} {angle}\r\n"
    ser.write(cmd.encode('utf-8'))
    print(f"发送: 舵机{servo_id} -> {angle}°")
    
    # 读取响应（可选）
    response = ""
    start_time = time.time()
    while time.time() - start_time < 0.5:  # 0.5秒超时
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='replace').strip()
            if line:
                response += line + "\n"
                if "degrees" in line:
                    break
    return response

# 获取一帧嘴部位置
def capture_mouth_position():
    """捕获一帧并检测嘴部位置"""
    # 初始化 MediaPipe Face Mesh
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(static_image_mode=True,  # 设为True以优化单帧分析
                                      max_num_faces=1,
                                      refine_landmarks=True,
                                      min_detection_confidence=0.5)

    # 嘴部的关键点索引
    MOUTH_LANDMARKS = list(set([i for pair in mp_face_mesh.FACEMESH_LIPS for i in pair]))
    
    # 尝试打开摄像头，先尝试索引0，如果失败再尝试其他索引
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("无法打开索引0的摄像头，尝试索引1...")
        cap = cv2.VideoCapture(1)
        if not cap.isOpened():
            print("无法打开任何摄像头")
            return None

    print("请将嘴部保持在摄像头视野中...")
    
    mouth_position = None
    countdown = 3  # 倒计时3秒
    
    while countdown >= 0:
        ret, frame = cap.read()
        if not ret:
            print("无法读取视频帧")
            break
            
        # 在画面上显示倒计时
        if countdown > 0:
            cv2.putText(frame, f"拍摄倒计时: {countdown}秒", 
                       (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.imshow('Camera', frame)
            cv2.waitKey(1000)  # 等待1秒
            countdown -= 1
            continue
        else:
            cv2.putText(frame, "保持不动！拍摄中...", 
                       (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow('Camera', frame)
            cv2.waitKey(500)  # 显示0.5秒
        
        # 分析图像
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb_frame)
        
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                img_h, img_w, _ = frame.shape
                
                # 收集所有嘴部关键点的坐标
                mouth_points = []
                for idx in MOUTH_LANDMARKS:
                    pt = face_landmarks.landmark[idx]
                    x, y = int(pt.x * img_w), int(pt.y * img_h)
                    mouth_points.append((x, y))
                    cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)
                
                # 计算嘴部中心点
                if mouth_points:
                    mouth_points_array = np.array(mouth_points)
                    center_x = int(np.mean(mouth_points_array[:, 0]))
                    center_y = int(np.mean(mouth_points_array[:, 1]))
                    
                    # 标记嘴部中心点
                    cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
                    
                    # 显示坐标
                    cv2.putText(frame, f"嘴部中心: ({center_x}, {center_y})", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    
                    mouth_position = (center_x, center_y)
            
            # 显示图像
            cv2.imshow('Camera', frame)
            cv2.waitKey(1000)  # 显示1秒
            break  # 检测到后立即退出循环
    
    # 释放资源
    cap.release()
    cv2.destroyAllWindows()
    
    return mouth_position

def main():
    try:
        # 捕获嘴部位置
        mouth_position = capture_mouth_position()
        
        if not mouth_position:
            print("未能检测到嘴部，程序退出")
            return
            
        print(f"已捕获嘴部中心点位置: {mouth_position}")
        
        # 打开串口
        ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=TIMEOUT)
        print(f"已连接到 {SERIAL_PORT}，波特率 {BAUDRATE}")
        print("嘴部位置舵机控制系统已启动")
        print("-" * 40)
        
        # 清空缓冲区
        ser.reset_input_buffer()
        
        # 计算舵机角度
        center_x, center_y = mouth_position
        
        # 将坐标映射到舵机角度
        x_angle = map_coordinate_to_angle(center_x, MOUTH_X_MIN, MOUTH_X_MAX, SERVO_X_MIN, SERVO_X_MAX)
        y_angle = map_coordinate_to_angle(center_y, MOUTH_Y_MIN, MOUTH_Y_MAX, SERVO_Y_MIN, SERVO_Y_MAX)
        
        # 反转Y轴方向（嘴部向上，舵机角度减小）
        y_angle = SERVO_Y_MAX - y_angle + SERVO_Y_MIN
        
        print(f"计算的舵机角度: X={x_angle}°, Y={y_angle}°")
        
        # 发送舵机控制命令
        response_x = set_servo_angle(ser, SERVO_X_ID, x_angle)
        response_y = set_servo_angle(ser, SERVO_Y_ID, y_angle)
        
        print("舵机控制完成")
        
        # 允许用户重新拍摄或退出
        while True:
            choice = input("\n输入'r'重新拍摄，输入'q'退出程序: ")
            if choice.lower() == 'q':
                break
            elif choice.lower() == 'r':
                # 重新捕获嘴部位置
                mouth_position = capture_mouth_position()
                if mouth_position:
                    center_x, center_y = mouth_position
                    x_angle = map_coordinate_to_angle(center_x, MOUTH_X_MIN, MOUTH_X_MAX, SERVO_X_MIN, SERVO_X_MAX)
                    y_angle = map_coordinate_to_angle(center_y, MOUTH_Y_MIN, MOUTH_Y_MAX, SERVO_Y_MIN, SERVO_Y_MAX)
                    y_angle = SERVO_Y_MAX - y_angle + SERVO_Y_MIN
                    
                    response_x = set_servo_angle(ser, SERVO_X_ID, x_angle)
                    response_y = set_servo_angle(ser, SERVO_Y_ID, y_angle)
                    print("舵机控制完成")
                else:
                    print("未能检测到嘴部")
            
    except serial.SerialException as e:
        print(f"串口错误: {e}")
        print(f"请确认设备已连接，并且COM端口号正确")
    except KeyboardInterrupt:
        print("\n程序已被用户中断")
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("串口已关闭")

if __name__ == "__main__":
    main()