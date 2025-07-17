import serial
import time
import cv2
import mediapipe as mp
import numpy as np
import threading
from mouth_track import get_mouth_data, detect_mouth_position

class RobotArmController:
    def __init__(self, serial_port='COM5', baudrate=115200):
        """初始化机器臂控制器"""
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.ser = None
        self.is_feeding = False
        self.log_callback = None  # 日志回调函数
        
        # 舵机初始位置
        self.servo_init_positions = {
            1: 90,   # 舵机1：水平面旋转
            2: 130,  # 舵机2：竖直面旋转
            3: 120,  # 舵机3
            4: 115   # 舵机4
        }
        
        # 喂食位置
        self.servo_feed_positions = {
            1: 120,  # 舵机1
            2: 45,   # 舵机2
            3: 120,  # 舵机3 不变
            4: 0     # 舵机4
        
            }
          # 初始化嘴部检测
        self.init_mouth_detection()
    
    def log(self, message, level="INFO"):
        """输出日志信息"""
        if self.log_callback:
            self.log_callback(message, level)
        else:
            print(f"[{level}] {message}")
    
    def init_mouth_detection(self):
        """初始化嘴部检测模块"""
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # 嘴部关键点索引
        self.MOUTH_LANDMARKS = list(set([i for pair in self.mp_face_mesh.FACEMESH_LIPS for i in pair]))
        
        # 摄像头
        self.cap = cv2.VideoCapture(1)
    
    def connect_serial(self):
        """连接串口"""
        try:
            self.ser = serial.Serial(self.serial_port, self.baudrate, timeout=1)
            self.log(f"已连接到 {self.serial_port}，波特率 {self.baudrate}")
            self.ser.reset_input_buffer()
            return True
        except serial.SerialException as e:
            self.log(f"串口连接失败: {e}", "ERROR")
            return False
    
    def send_servo_command(self, servo_id, angle):
        """发送舵机控制命令"""
        if not self.ser or not self.ser.is_open:
            self.log("串口未连接", "WARNING")
            return False
            
        try:
            cmd = f"set_servo_angle {servo_id} {angle}\r\n"
            self.ser.write(cmd.encode('utf-8'))
            self.log(f"发送命令: 舵机{servo_id} -> {angle}度")
            
            # 读取响应
            response = ""
            start_time = time.time()
            while time.time() - start_time < 1:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8', errors='replace').strip()
                    if line:
                        response += line + "\n"
                        if "degrees" in line:
                            break
            
            if response:
                self.log(f"舵机响应: {response.strip()}")
            
            return True
        except Exception as e:
            self.log(f"发送命令失败: {e}", "ERROR")
            return False
    
    def initialize_servos(self):
        """初始化所有舵机到初始位置"""
        self.log("正在初始化机器臂...")
        for servo_id, angle in self.servo_init_positions.items():
            if self.send_servo_command(servo_id, angle):
                time.sleep(0.2)  # 每个舵机之间的延时
            else:
                self.log(f"舵机{servo_id}初始化失败", "ERROR")
                return False
        self.log("机器臂初始化完成")
        return True
    
    def calculate_servo_angles(self, offset_x, offset_y, image_width, image_height):
        """
        根据嘴部偏移量计算舵机角度
        offset_x: 水平偏移量（正值向右，负值向左）
        offset_y: 垂直偏移量（正值向下，负值向上）
        """
        # 舵机1角度范围：90-150度（水平控制）
        servo1_min, servo1_max = 90, 150
        servo1_center = 120  # 中心位置对应120度
        
        # 舵机2角度范围：20-60度（垂直控制）
        servo2_min, servo2_max = 20, 60
        servo2_center = 45   # 中心位置对应45度
        
        # 计算偏移量的归一化值（-1到1之间）
        max_offset_x = image_width // 3  # 使用图像宽度的1/3作为最大有效偏移
        max_offset_y = image_height // 3  # 使用图像高度的1/3作为最大有效偏移
        
        normalized_x = max(-1, min(1, offset_x / max_offset_x))
        normalized_y = max(-1, min(1, offset_y / max_offset_y))
        
        # 计算舵机角度
        # 舵机1：向右偏移减小角度，向左偏移增大角度
        servo1_angle = servo1_center - (normalized_x * (servo1_max - servo1_min) / 2)
        servo1_angle = max(servo1_min, min(servo1_max, int(servo1_angle)))
        
        # 舵机2：向上偏移减小角度，向下偏移增大角度
        servo2_angle = servo2_center + (normalized_y * (servo2_max - servo2_min) / 2)
        servo2_angle = max(servo2_min, min(servo2_max, int(servo2_angle)))
        
        return servo1_angle, servo2_angle
    
    def detect_mouth_single_frame(self):
        """截取一帧检测嘴部并返回位置信息"""
        if not self.cap.isOpened():
            print("摄像头未打开")
            return False, None, None, 0, 0
        
        # 使用mouth_track模块的检测函数
        is_detected, mouth_center, image_center, offset_x, offset_y = detect_mouth_position(self.cap)
        if is_detected:
            self.log(f"检测到嘴部:")
            self.log(f"  嘴部中心: {mouth_center}")
            self.log(f"  图像中心: {image_center}")
            self.log(f"  水平偏移: {offset_x} ({'右' if offset_x > 0 else '左' if offset_x < 0 else '居中'})")
            self.log(f"  垂直偏移: {offset_y} ({'下' if offset_y > 0 else '上' if offset_y < 0 else '居中'})")
            
            # 获取图像尺寸用于角度计算
            success, frame = self.cap.read()
            if success:
                img_h, img_w = frame.shape[:2]
                
                # 显示检测结果
                cv2.circle(frame, mouth_center, 5, (0, 0, 255), -1)  # 嘴部中心
                cv2.circle(frame, image_center, 5, (255, 0, 0), -1)  # 图像中心
                cv2.line(frame, image_center, mouth_center, (0, 255, 0), 2)  # 连线
                
                cv2.putText(frame, f"Mouth: {mouth_center}", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.putText(frame, f"Center: {image_center}", 
                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                cv2.putText(frame, f"Offset: ({offset_x}, {offset_y})", 
                           (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                cv2.imshow('Mouth Detection', frame)
                cv2.waitKey(2000)  # 显示2秒
                cv2.destroyAllWindows()
                
                return True, mouth_center, image_center, offset_x, offset_y, img_w, img_h
        else:
            print("未检测到嘴部")
            # 显示未检测到的帧
            success, frame = self.cap.read()
            if success:
                cv2.putText(frame, "No mouth detected", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.imshow('Mouth Detection', frame)
                cv2.waitKey(1000)
                cv2.destroyAllWindows()
        
        return False, None, None, 0, 0, 0, 0
    
    def start_feeding(self):
        """开始喂食"""
        if self.is_feeding:
            print("已经在喂食状态中")
            return
        
        print("开始喂食序列...")
        
        # 1. 截取一帧检测嘴部
        is_detected, mouth_center, image_center, offset_x, offset_y, img_w, img_h = self.detect_mouth_single_frame()
        
        if is_detected:
            print("检测到嘴部，开始执行喂食动作")
            self.is_feeding = True
            
            # 2. 根据嘴部位置计算舵机角度
            servo1_angle, servo2_angle = self.calculate_servo_angles(offset_x, offset_y, img_w, img_h)
            
            print(f"根据嘴部位置调整舵机角度:")
            print(f"  舵机1 (水平): {servo1_angle}度")
            print(f"  舵机2 (垂直): {servo2_angle}度")
            
            # 3. 执行舵机动作序列
            # 舵机1：根据水平位置调整
            self.send_servo_command(1, servo1_angle)
            time.sleep(0.5)
            
            # 舵机2：根据垂直位置调整
            self.send_servo_command(2, servo2_angle)
            time.sleep(0.5)
            
            # 舵机3保持不变，延时1秒
            print("等待1秒...")
            time.sleep(1)
            
            # 舵机4：0度（喂食动作）
            self.send_servo_command(4, self.servo_feed_positions[4])
            
            print("喂食动作完成")
            
            # 显示最终角度信息
            print(f"最终舵机位置:")
            print(f"  舵机1: {servo1_angle}度 (范围: 90-150)")
            print(f"  舵机2: {servo2_angle}度 (范围: 20-60)")
            print(f"  舵机3: {self.servo_init_positions[3]}度 (保持不变)")
            print(f"  舵机4: {self.servo_feed_positions[4]}度 (喂食位置)")
            
        else:
            print("未检测到嘴部，取消喂食动作")
    
    def stop_feeding(self):
        """停止喂食，复位所有舵机"""
        print("停止喂食，复位机器臂...")
        self.is_feeding = False
        
        # 复位所有舵机到初始位置
        for servo_id, angle in self.servo_init_positions.items():
            if self.send_servo_command(servo_id, angle):
                time.sleep(0.3)  # 每个舵机之间的延时
            else:
                print(f"舵机{servo_id}复位失败")
        
        print("机器臂已复位到初始状态")
    
    def dynamic_feeding_mode(self):
        """动态喂食模式：实时根据嘴部位置调整舵机"""
        print("进入动态喂食模式...")
        print("按 'q' 键退出动态模式")
        
        if not self.cap.isOpened():
            print("摄像头未打开")
            return
        
        self.is_feeding = True
        last_servo1_angle = self.servo_init_positions[1]
        last_servo2_angle = self.servo_init_positions[2]
        
        # 设置舵机3为喂食位置，舵机4为0度
        self.send_servo_command(3, self.servo_init_positions[3])
        time.sleep(0.2)
        self.send_servo_command(4, 0)
        time.sleep(0.5)
        
        try:
            while True:
                success, frame = self.cap.read()
                if not success:
                    continue
                
                img_h, img_w = frame.shape[:2]
                image_center = (img_w // 2, img_h // 2)
                
                # 检测嘴部位置
                is_detected, mouth_center, _, offset_x, offset_y = detect_mouth_position(self.cap)
                
                if is_detected:
                    # 计算新的舵机角度
                    servo1_angle, servo2_angle = self.calculate_servo_angles(offset_x, offset_y, img_w, img_h)
                    
                    # 只有角度变化超过阈值才发送命令，避免频繁调整
                    if abs(servo1_angle - last_servo1_angle) >= 2:
                        self.send_servo_command(1, servo1_angle)
                        last_servo1_angle = servo1_angle
                    
                    if abs(servo2_angle - last_servo2_angle) >= 2:
                        self.send_servo_command(2, servo2_angle)
                        last_servo2_angle = servo2_angle
                    
                    # 显示信息
                    cv2.circle(frame, mouth_center, 5, (0, 0, 255), -1)  # 嘴部中心
                    cv2.circle(frame, image_center, 5, (255, 0, 0), -1)  # 图像中心
                    cv2.line(frame, image_center, mouth_center, (0, 255, 0), 2)  # 连线
                    
                    cv2.putText(frame, f"Mouth: {mouth_center}", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    cv2.putText(frame, f"Offset: ({offset_x}, {offset_y})", 
                               (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv2.putText(frame, f"Servo1: {servo1_angle}, Servo2: {servo2_angle}", 
                               (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                    cv2.putText(frame, "Press 'q' to exit", 
                               (10, img_h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                else:
                    cv2.putText(frame, "No mouth detected", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    cv2.putText(frame, "Press 'q' to exit", 
                               (10, img_h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                cv2.imshow('Dynamic Feeding Mode', frame)
                
                # 检查退出键
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                    
                time.sleep(0.1)  # 控制帧率
        
        except KeyboardInterrupt:
            print("动态模式被中断")
        finally:
            cv2.destroyAllWindows()
            self.is_feeding = False
            print("退出动态喂食模式")
    
    def run_terminal(self):
        """运行终端控制界面"""
        print("="*50)
        print("机器臂喂食控制终端")
        print("="*50)
        print("可用命令:")
        print("1. start   - 开始喂食（单次检测）")
        print("2. dynamic - 动态喂食模式（实时跟踪）")
        print("3. stop    - 停止喂食")
        print("4. init    - 重新初始化舵机")
        print("5. exit    - 退出程序")
        print("="*50)
        
        # 连接串口
        if not self.connect_serial():
            print("串口连接失败，程序退出")
            return
        
        # 初始化舵机
        if not self.initialize_servos():
            print("舵机初始化失败，程序退出")
            return
        
        # 主控制循环
        while True:
            try:
                command = input("\n请输入命令: ").strip().lower()
                
                if command == "start":
                    self.start_feeding()
                elif command == "dynamic":
                    self.dynamic_feeding_mode()
                elif command == "stop":
                    self.stop_feeding()
                elif command == "init":
                    self.initialize_servos()
                elif command == "exit":
                    print("正在退出程序...")
                    break
                else:
                    print("无效命令，请输入: start, dynamic, stop, init, 或 exit")
                    
            except KeyboardInterrupt:
                print("\n程序被用户中断")
                break
            except Exception as e:
                print(f"发生错误: {e}")
        
        # 清理资源
        self.cleanup()
    
    def cleanup(self):
        """清理资源"""
        print("正在清理资源...")
        
        # 停止喂食并复位
        if self.is_feeding:
            self.stop_feeding()
        
        # 关闭摄像头
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
        
        # 关闭串口
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("串口已关闭")
        
        # 关闭所有OpenCV窗口
        cv2.destroyAllWindows()
        print("资源清理完成")

def main():
    """主函数"""
    # 创建机器臂控制器实例
    controller = RobotArmController(serial_port='COM5', baudrate=115200)
    
    # 运行终端界面
    controller.run_terminal()

if __name__ == "__main__":
    main()