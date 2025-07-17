#!/usr/bin/env python3
"""
机器臂智能喂食控制应用程序
图形界面版本
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import queue
import time
import sys
import os
from datetime import datetime

# 导入核心控制模块
from calculate_angle import RobotArmController

class FeedingControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("智能机器臂喂食控制系统 v1.0")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 设置窗口图标（如果有的话）
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass
        
        # 初始化变量
        self.controller = None
        self.is_connected = False
        self.log_queue = queue.Queue()
        self.status_text = tk.StringVar(value="未连接")
        
        # 创建界面
        self.create_widgets()
        self.setup_logging()
        
        # 启动日志更新线程
        self.update_log_display()
        
    def create_widgets(self):
        """创建主界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="智能机器臂喂食控制系统", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # 连接设置框架
        connection_frame = ttk.LabelFrame(main_frame, text="连接设置", padding="10")
        connection_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 串口设置
        ttk.Label(connection_frame, text="串口:").grid(row=0, column=0, sticky=tk.W)
        self.port_var = tk.StringVar(value="COM5")
        port_combo = ttk.Combobox(connection_frame, textvariable=self.port_var, 
                                 values=["COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8"])
        port_combo.grid(row=0, column=1, padx=(5, 20), sticky=(tk.W, tk.E))
        
        # 波特率设置
        ttk.Label(connection_frame, text="波特率:").grid(row=0, column=2, sticky=tk.W)
        self.baudrate_var = tk.StringVar(value="115200")
        baudrate_combo = ttk.Combobox(connection_frame, textvariable=self.baudrate_var,
                                     values=["9600", "38400", "57600", "115200"])
        baudrate_combo.grid(row=0, column=3, padx=(5, 20), sticky=(tk.W, tk.E))
        
        # 连接按钮
        self.connect_btn = ttk.Button(connection_frame, text="连接", command=self.connect_device)
        self.connect_btn.grid(row=0, column=4, padx=(5, 0))
        
        # 状态显示
        status_frame = ttk.Frame(connection_frame)
        status_frame.grid(row=1, column=0, columnspan=5, sticky=(tk.W, tk.E), pady=(10, 0))
        ttk.Label(status_frame, text="状态:").pack(side=tk.LEFT)
        status_label = ttk.Label(status_frame, textvariable=self.status_text, 
                                foreground="red", font=("Arial", 10, "bold"))
        status_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # 控制按钮框架
        control_frame = ttk.LabelFrame(main_frame, text="控制面板", padding="10")
        control_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # 控制按钮
        btn_style = {"width": 15, "pady": 5}
        
        self.init_btn = ttk.Button(control_frame, text="初始化舵机", 
                                  command=self.initialize_servos, **btn_style)
        self.init_btn.grid(row=0, column=0, pady=5, sticky=tk.W)
        
        self.start_btn = ttk.Button(control_frame, text="开始喂食", 
                                   command=self.start_feeding, **btn_style)
        self.start_btn.grid(row=1, column=0, pady=5, sticky=tk.W)
        
        self.dynamic_btn = ttk.Button(control_frame, text="动态跟踪", 
                                     command=self.start_dynamic_mode, **btn_style)
        self.dynamic_btn.grid(row=2, column=0, pady=5, sticky=tk.W)
        
        self.stop_btn = ttk.Button(control_frame, text="停止喂食", 
                                  command=self.stop_feeding, **btn_style)
        self.stop_btn.grid(row=3, column=0, pady=5, sticky=tk.W)
        
        # 分隔线
        ttk.Separator(control_frame, orient='horizontal').grid(row=4, column=0, 
                                                              sticky=(tk.W, tk.E), pady=20)
        
        # 手动控制
        manual_label = ttk.Label(control_frame, text="手动控制舵机:", font=("Arial", 10, "bold"))
        manual_label.grid(row=5, column=0, sticky=tk.W, pady=(0, 10))
        
        # 舵机控制
        for i in range(1, 5):
            servo_frame = ttk.Frame(control_frame)
            servo_frame.grid(row=5+i, column=0, sticky=(tk.W, tk.E), pady=2)
            
            ttk.Label(servo_frame, text=f"舵机{i}:").pack(side=tk.LEFT)
            
            angle_var = tk.StringVar(value="90")
            setattr(self, f"servo{i}_var", angle_var)
            
            angle_entry = ttk.Entry(servo_frame, textvariable=angle_var, width=8)
            angle_entry.pack(side=tk.LEFT, padx=(5, 5))
            
            ttk.Label(servo_frame, text="度").pack(side=tk.LEFT)
            
            set_btn = ttk.Button(servo_frame, text="设置", width=8,
                               command=lambda servo_id=i: self.set_servo_angle(servo_id))
            set_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        # 日志显示框架
        log_frame = ttk.LabelFrame(main_frame, text="运行日志", padding="10")
        log_frame.grid(row=2, column=1, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # 日志文本框
        self.log_text = scrolledtext.ScrolledText(log_frame, width=50, height=20, 
                                                 wrap=tk.WORD, font=("Consolas", 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 清除日志按钮
        clear_btn = ttk.Button(log_frame, text="清除日志", command=self.clear_log)
        clear_btn.grid(row=1, column=0, pady=(10, 0))
        
        # 初始状态设置
        self.update_button_states(False)
        
    def setup_logging(self):
        """设置日志系统"""
        self.log_message("应用程序启动")
        self.log_message("等待连接设备...")
        
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
        
    def connect_device(self):
        """连接设备"""
        if self.is_connected:
            self.disconnect_device()
            return
            
        port = self.port_var.get()
        baudrate = int(self.baudrate_var.get())
        
        self.log_message(f"正在连接到 {port}, 波特率: {baudrate}")
        
        try:
            # 在新线程中初始化控制器
            def init_controller():
                self.controller = RobotArmController(serial_port=port, baudrate=baudrate)
                # 重定向控制器的输出到我们的日志系统
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
        self.connect_btn.config(text="断开连接")
        self.update_button_states(True)
        self.log_message("设备连接成功")
        
        # 自动初始化舵机
        self.root.after(1000, self.auto_initialize)
        
    def on_connection_failure(self):
        """连接失败回调"""
        self.log_message("设备连接失败", "ERROR")
        messagebox.showerror("连接失败", "无法连接到设备，请检查串口设置")
        
    def disconnect_device(self):
        """断开设备连接"""
        if self.controller:
            self.controller.cleanup()
        
        self.is_connected = False
        self.status_text.set("未连接")
        self.connect_btn.config(text="连接")
        self.update_button_states(False)
        self.controller = None
        self.log_message("设备已断开连接")
        
    def update_button_states(self, connected):
        """更新按钮状态"""
        state = tk.NORMAL if connected else tk.DISABLED
        self.init_btn.config(state=state)
        self.start_btn.config(state=state)
        self.dynamic_btn.config(state=state)
        self.stop_btn.config(state=state)
        
        # 更新状态显示颜色
        if connected:
            self.status_text.set("已连接")
            self.root.nametowidget(str(self.root) + ".!frame.!labelframe2.!frame.!label2").config(foreground="green")
        else:
            self.status_text.set("未连接")
            self.root.nametowidget(str(self.root) + ".!frame.!labelframe2.!frame.!label2").config(foreground="red")
    
    def auto_initialize(self):
        """自动初始化舵机"""
        self.log_message("正在自动初始化舵机...")
        threading.Thread(target=self.controller.initialize_servos, daemon=True).start()
        
    def initialize_servos(self):
        """初始化舵机"""
        if not self.is_connected:
            messagebox.showwarning("警告", "请先连接设备")
            return
            
        self.log_message("手动初始化舵机...")
        threading.Thread(target=self.controller.initialize_servos, daemon=True).start()
        
    def start_feeding(self):
        """开始喂食"""
        if not self.is_connected:
            messagebox.showwarning("警告", "请先连接设备")
            return
            
        self.log_message("开始单次喂食...")
        threading.Thread(target=self.controller.start_feeding, daemon=True).start()
        
    def start_dynamic_mode(self):
        """开始动态跟踪模式"""
        if not self.is_connected:
            messagebox.showwarning("警告", "请先连接设备")
            return
            
        self.log_message("启动动态跟踪模式...")
        
        # 在新窗口中显示提示
        result = messagebox.showinfo("动态跟踪模式", 
                                   "即将启动动态跟踪模式\n\n"
                                   "操作提示:\n"
                                   "- 将显示摄像头画面\n"
                                   "- 机器臂将实时跟踪嘴部位置\n"
                                   "- 按 'q' 键退出跟踪模式\n\n"
                                   "请确保面部清晰可见")
        
        threading.Thread(target=self.controller.dynamic_feeding_mode, daemon=True).start()
        
    def stop_feeding(self):
        """停止喂食"""
        if not self.is_connected:
            messagebox.showwarning("警告", "请先连接设备")
            return
            
        self.log_message("停止喂食，复位机器臂...")
        threading.Thread(target=self.controller.stop_feeding, daemon=True).start()
        
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
            
    def on_closing(self):
        """应用程序关闭事件"""
        if self.is_connected:
            self.log_message("正在断开连接...")
            self.disconnect_device()
        
        self.log_message("应用程序即将退出")
        self.root.after(500, self.root.destroy)

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
