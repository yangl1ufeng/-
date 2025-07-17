#!/usr/bin/env python3
"""
机器臂智能喂食控制应用程序
集成控制版本
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import queue
import time
import subprocess
import sys
import os
from datetime import datetime

# 导入核心控制模块
try:
    from calculate_angle import RobotArmController
    CONTROLLER_AVAILABLE = True
except ImportError:
    CONTROLLER_AVAILABLE = False

class FeedingControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("智能机器臂喂食控制系统")
        self.root.geometry("800x700")
        
        # 初始化变量
        self.controller = None
        self.is_connected = False
        self.log_queue = queue.Queue()
        self.status_text = tk.StringVar(value="未连接")
        
        # 创建界面
        self.create_widgets()
        self.update_log_display()
        
        # 如果控制器可用，显示完整功能
        if not CONTROLLER_AVAILABLE:
            self.log_message("警告: 无法导入控制模块，部分功能不可用", "WARNING")
    
    def create_widgets(self):
        """创建主界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="智能机器臂喂食控制系统", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 连接设置框架
        connection_frame = ttk.LabelFrame(main_frame, text="连接设置", padding="10")
        connection_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 串口设置行
        port_frame = ttk.Frame(connection_frame)
        port_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(port_frame, text="串口:").pack(side=tk.LEFT)
        self.port_var = tk.StringVar(value="COM5")
        port_combo = ttk.Combobox(port_frame, textvariable=self.port_var, width=10,
                                 values=["COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8"])
        port_combo.pack(side=tk.LEFT, padx=(5, 20))
        
        ttk.Label(port_frame, text="波特率:").pack(side=tk.LEFT)
        self.baudrate_var = tk.StringVar(value="115200")
        baudrate_combo = ttk.Combobox(port_frame, textvariable=self.baudrate_var, width=10,
                                     values=["9600", "38400", "57600", "115200"])
        baudrate_combo.pack(side=tk.LEFT, padx=(5, 20))
        
        # 连接按钮
        self.connect_btn = ttk.Button(port_frame, text="连接设备", command=self.connect_device)
        self.connect_btn.pack(side=tk.LEFT, padx=(20, 0))
        
        # 状态显示
        status_frame = ttk.Frame(connection_frame)
        status_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(status_frame, text="状态:").pack(side=tk.LEFT)
        self.status_label = ttk.Label(status_frame, textvariable=self.status_text, 
                                     foreground="red", font=("Arial", 10, "bold"))
        self.status_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # 主控制面板框架
        control_main_frame = ttk.Frame(main_frame)
        control_main_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # 左侧控制面板
        left_frame = ttk.Frame(control_main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # 主要控制按钮框架
        main_control_frame = ttk.LabelFrame(left_frame, text="主要控制", padding="10")
        main_control_frame.pack(fill=tk.X, pady=(0, 10))
          # 控制按钮 - 对应用户要求的5个命令
        btn_style = {"width": 18}
        
        self.start_btn = ttk.Button(main_control_frame, text="1. 开始喂食", 
                                   command=self.start_feeding, **btn_style)
        self.start_btn.pack(fill=tk.X, pady=8, ipady=4)
        
        self.dynamic_btn = ttk.Button(main_control_frame, text="2. 动态跟踪模式", 
                                     command=self.dynamic_feeding, **btn_style)
        self.dynamic_btn.pack(fill=tk.X, pady=8, ipady=4)
        
        self.stop_btn = ttk.Button(main_control_frame, text="3. 停止喂食", 
                                  command=self.stop_feeding, **btn_style)
        self.stop_btn.pack(fill=tk.X, pady=8, ipady=4)
        
        self.init_btn = ttk.Button(main_control_frame, text="4. 初始化舵机", 
                                  command=self.init_servos, **btn_style)
        self.init_btn.pack(fill=tk.X, pady=8, ipady=4)
        
        self.exit_btn = ttk.Button(main_control_frame, text="5. 退出程序", 
                                  command=self.exit_program, **btn_style)
        self.exit_btn.pack(fill=tk.X, pady=8, ipady=4)
        
        # 分隔线
        ttk.Separator(main_control_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # 快速测试按钮
        test_frame = ttk.LabelFrame(left_frame, text="设备测试", padding="10")
        test_frame.pack(fill=tk.X, pady=(0, 10))
        
        test_btn_style = {"width": 18}
        
        self.test_camera_btn = ttk.Button(test_frame, text="测试摄像头", 
                                        command=self.test_camera, **test_btn_style)
        self.test_camera_btn.pack(fill=tk.X, pady=2)
        
        self.test_serial_btn = ttk.Button(test_frame, text="测试串口", 
                                        command=self.test_serial, **test_btn_style)
        self.test_serial_btn.pack(fill=tk.X, pady=2)
        
        self.test_mouth_btn = ttk.Button(test_frame, text="测试嘴部检测", 
                                       command=self.test_mouth_detection, **test_btn_style)
        self.test_mouth_btn.pack(fill=tk.X, pady=2)
        
        # 手动舵机控制
        manual_frame = ttk.LabelFrame(left_frame, text="手动控制", padding="10")
        manual_frame.pack(fill=tk.X)
        
        for i in range(1, 5):
            servo_frame = ttk.Frame(manual_frame)
            servo_frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(servo_frame, text=f"舵机{i}:", width=6).pack(side=tk.LEFT)
            
            angle_var = tk.StringVar(value="90")
            setattr(self, f"servo{i}_var", angle_var)
            
            angle_entry = ttk.Entry(servo_frame, textvariable=angle_var, width=6)
            angle_entry.pack(side=tk.LEFT, padx=(2, 2))
            
            ttk.Label(servo_frame, text="°").pack(side=tk.LEFT)
            
            set_btn = ttk.Button(servo_frame, text="设置", width=6,
                               command=lambda servo_id=i: self.set_servo_angle(servo_id))
            set_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        # 右侧日志显示框架
        log_frame = ttk.LabelFrame(control_main_frame, text="运行日志", padding="10")
        log_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 日志文本框
        self.log_text = scrolledtext.ScrolledText(log_frame, width=50, height=25, 
                                                 wrap=tk.WORD, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 日志控制按钮
        log_btn_frame = ttk.Frame(log_frame)
        log_btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(log_btn_frame, text="清除日志", command=self.clear_log).pack(side=tk.LEFT)
        ttk.Button(log_btn_frame, text="保存日志", command=self.save_log).pack(side=tk.LEFT, padx=(10, 0))
        
        # 初始化按钮状态
        self.update_button_states(False)
          # 初始日志
        self.log_message("应用程序启动完成")
        self.log_message("请连接设备后使用控制功能")
    
    def update_button_states(self, connected):
        """更新按钮状态"""
        state = tk.NORMAL if connected else tk.DISABLED
        self.start_btn.config(state=state)
        self.dynamic_btn.config(state=state)
        self.stop_btn.config(state=state)
        self.init_btn.config(state=state)
        
        # 更新连接按钮文本
        if connected:
            self.connect_btn.config(text="断开连接")
            self.status_label.config(foreground="green")
        else:
            self.connect_btn.config(text="连接设备")
            self.status_label.config(foreground="red")
    
    def connect_device(self):
        """连接或断开设备"""
        if self.is_connected:
            self.disconnect_device()
            return
            
        if not CONTROLLER_AVAILABLE:
            messagebox.showerror("错误", "控制模块未加载，无法连接设备")
            return
            
        port = self.port_var.get()
        baudrate = int(self.baudrate_var.get())
        
        self.log_message(f"正在连接到 {port}, 波特率: {baudrate}")
        
        try:
            # 在新线程中初始化控制器
            def init_controller():
                self.controller = RobotArmController(serial_port=port, baudrate=baudrate)
                # 设置日志回调
                self.controller.log_callback = self.log_message
                
                if self.controller.connect_serial():
                    self.root.after(0, self.on_connection_success)
                else:
                    self.root.after(0, self.on_connection_failure)
            
            threading.Thread(target=init_controller, daemon=True).start()
            
        except Exception as e:
            self.log_message(f"连接失败: {e}", "ERROR")
            messagebox.showerror("连接错误", f"无法连接到设备: {e}")
    
    def on_connection_success(self):
        """连接成功回调"""
        self.is_connected = True
        self.status_text.set("已连接")
        self.update_button_states(True)
        self.log_message("设备连接成功")
        
        # 自动初始化舵机
        self.root.after(1000, lambda: threading.Thread(target=self.controller.initialize_servos, daemon=True).start())
        
    def on_connection_failure(self):
        """连接失败回调"""
        self.log_message("设备连接失败", "ERROR")
        messagebox.showerror("连接失败", "无法连接到设备，请检查串口设置")
        
    def disconnect_device(self):
        """断开设备连接"""
        if self.controller:
            try:
                self.controller.cleanup()
            except:
                pass
        
        self.is_connected = False
        self.status_text.set("未连接")
        self.update_button_states(False)
        self.controller = None
        self.log_message("设备已断开连接")
    
    # === 主要控制功能 ===
    
    def start_feeding(self):
        """1. 开始喂食（单次检测）"""
        if not self.is_connected:
            messagebox.showwarning("警告", "请先连接设备")
            return
            
        self.log_message("执行命令: 开始喂食（单次检测）")
        threading.Thread(target=self.controller.start_feeding, daemon=True).start()
        
    def dynamic_feeding(self):
        """2. 动态跟踪模式"""
        if not self.is_connected:
            messagebox.showwarning("警告", "请先连接设备")
            return
            
        self.log_message("执行命令: 动态跟踪模式")
        
        # 显示提示信息
        result = messagebox.showinfo("动态跟踪模式", 
                                   "即将启动动态跟踪模式\n\n"
                                   "操作提示:\n"
                                   "- 将显示摄像头画面\n"
                                   "- 机器臂将实时跟踪嘴部位置\n"
                                   "- 按 'q' 键退出跟踪模式\n\n"
                                   "请确保面部清晰可见")
        
        threading.Thread(target=self.controller.dynamic_feeding_mode, daemon=True).start()
        
    def stop_feeding(self):
        """3. 停止喂食"""
        if not self.is_connected:
            messagebox.showwarning("警告", "请先连接设备")
            return
            
        self.log_message("执行命令: 停止喂食")
        threading.Thread(target=self.controller.stop_feeding, daemon=True).start()
        
    def init_servos(self):
        """4. 初始化舵机"""
        if not self.is_connected:
            messagebox.showwarning("警告", "请先连接设备")
            return
            
        self.log_message("执行命令: 初始化舵机")
        threading.Thread(target=self.controller.initialize_servos, daemon=True).start()
        
    def exit_program(self):
        """5. 退出程序"""
        result = messagebox.askyesno("确认退出", "确定要退出程序吗？")
        if result:
            self.log_message("执行命令: 退出程序")
            self.on_closing()
    
    def set_servo_angle(self, servo_id):
        """设置舵机角度"""
        if not self.is_connected:
            messagebox.showwarning("警告", "请先连接设备")
            return
            
        try:
            angle_var = getattr(self, f"servo{servo_id}_var")
            angle = int(angle_var.get())
            
            if not (0 <= angle <= 180):
                messagebox.showerror("错误", "角度必须在0-180度之间")
                return
                
            self.log_message(f"手动设置舵机{servo_id}到{angle}度")
            threading.Thread(target=lambda: self.controller.send_servo_command(servo_id, angle), 
                           daemon=True).start()
            
        except ValueError:
            messagebox.showerror("错误", "请输入有效的角度值")
        
    def log_message(self, message, level="INFO"):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {level}: {message}"
        self.log_queue.put(formatted_message)
        
    def update_log_display(self):
        """更新日志显示"""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.insert(tk.END, message + "\n")
                self.log_text.see(tk.END)
        except queue.Empty:
            pass
        
        # 定时更新
        self.root.after(100, self.update_log_display)
        
    def clear_log(self):
        """清除日志"""
        self.log_text.delete(1.0, tk.END)
        self.log_message("日志已清除")
        
    def save_log(self):
        """保存日志"""
        try:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
            )
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get(1.0, tk.END))
                self.log_message(f"日志已保存到: {filename}")
        except Exception as e:
            self.log_message(f"保存日志失败: {e}", "ERROR")
    
    def start_terminal_mode(self):
        """启动终端控制模式"""
        self.log_message("启动终端控制模式...")
        try:
            # 运行原来的终端程序
            subprocess.Popen([sys.executable, "calculate_angle.py"], 
                           cwd=os.path.dirname(os.path.abspath(__file__)))
            self.log_message("终端控制程序已启动")
        except Exception as e:
            self.log_message(f"启动终端模式失败: {e}", "ERROR")
            messagebox.showerror("错误", f"无法启动终端模式: {e}")
    
    def start_gui_mode(self):
        """启动完整图形界面模式"""
        self.log_message("启动完整图形界面模式...")
        try:
            # 这里可以启动完整的GUI应用
            messagebox.showinfo("提示", "完整图形界面功能正在开发中\n请使用终端控制模式")
        except Exception as e:
            self.log_message(f"启动GUI模式失败: {e}", "ERROR")
    
    def test_camera(self):
        """测试摄像头"""
        self.log_message("正在测试摄像头...")
        
        def camera_test():
            try:
                import cv2
                cap = cv2.VideoCapture(1)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret:
                        self.log_message("摄像头测试成功")
                        cv2.imshow("Camera Test", frame)
                        cv2.waitKey(2000)
                        cv2.destroyAllWindows()
                    else:
                        self.log_message("摄像头无法读取图像", "ERROR")
                    cap.release()
                else:
                    self.log_message("无法打开摄像头", "ERROR")
            except Exception as e:
                self.log_message(f"摄像头测试失败: {e}", "ERROR")
        
        threading.Thread(target=camera_test, daemon=True).start()
    
    def test_serial(self):
        """测试串口"""
        port = self.port_var.get()
        baudrate = self.baudrate_var.get()
        self.log_message(f"正在测试串口 {port} (波特率: {baudrate})")
        
        def serial_test():
            try:
                import serial
                ser = serial.Serial(port, int(baudrate), timeout=1)
                self.log_message("串口连接成功")
                ser.close()
                self.log_message("串口测试完成")
            except Exception as e:
                self.log_message(f"串口测试失败: {e}", "ERROR")
        
        threading.Thread(target=serial_test, daemon=True).start()
    
    def test_mouth_detection(self):
        """测试嘴部检测"""
        self.log_message("正在测试嘴部检测...")
        
        def mouth_test():
            try:
                # 运行嘴部检测测试
                subprocess.Popen([sys.executable, "mouth_track.py"], 
                               cwd=os.path.dirname(os.path.abspath(__file__)))
                self.log_message("嘴部检测程序已启动")
            except Exception as e:
                self.log_message(f"嘴部检测测试失败: {e}", "ERROR")
        
        threading.Thread(target=mouth_test, daemon=True).start()
    
    def on_closing(self):
        """应用程序关闭事件"""
        self.log_message("应用程序即将退出")
        self.root.destroy()

def main():
    """主函数"""
    # 创建主窗口
    root = tk.Tk()
      # 创建应用程序实例
    app = FeedingControlApp(root)
    
    # 设置关闭事件
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # 启动GUI事件循环
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("应用程序被用户中断")

if __name__ == "__main__":
    main()
