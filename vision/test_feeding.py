#!/usr/bin/env python3
"""
测试喂食控制程序
"""

from calculate_angle import RobotArmController

def main():
    print("测试机器臂喂食控制程序")
    print("确保以下设备已连接:")
    print("1. 串口设备 (COM5)")
    print("2. 摄像头 (设备1)")
    print("3. 机器臂舵机")
    print("-" * 40)
    
    input("按回车键继续...")
    
    # 创建控制器实例
    controller = RobotArmController(serial_port='COM5', baudrate=115200)
    
    # 运行主程序
    controller.run_terminal()

if __name__ == "__main__":
    main()
