import serial
import time

# 串口配置
SERIAL_PORT = 'COM5'  # 替换成你的USB虚拟串口号
BAUDRATE = 115200
TIMEOUT = 1

def main():
    try:
        # 打开串口
        ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=TIMEOUT)
        print(f"已连接到 {SERIAL_PORT}，波特率 {BAUDRATE}")
        print("RTThread 舵机控制终端")
        print("-" * 40)
        print("命令格式: set_servo_angle [舵机ID 1-4] [角度 0-180]")
        print("输入 'exit' 退出程序")
        print("-" * 40)
        
        # 清空缓冲区
        ser.reset_input_buffer()
        
        while True:
            # 获取用户输入
            servo_id = input("舵机号 (1-4): ")
            
            # 检查退出条件
            if servo_id.lower() == 'exit':
                break
                
            angle = input("角度 (0-180): ")
            
            # 验证输入
            if servo_id.isdigit() and angle.isdigit():
                servo_id = int(servo_id)
                angle = int(angle)
                
                if 1 <= servo_id <= 4 and 0 <= angle <= 180:
                    # 构建RTThread MSH命令
                    cmd = f"set_servo_angle {servo_id} {angle}\r\n"
                    ser.write(cmd.encode('utf-8'))
                    print(f"已发送: {cmd.strip()}")
                    
                    # 读取响应（带超时）
                    response = ""
                    start_time = time.time()
                    while time.time() - start_time < 1:  # 1秒超时
                        if ser.in_waiting > 0:
                            line = ser.readline().decode('utf-8', errors='replace').strip()
                            if line:
                                response += line + "\n"
                                # 如果收到足够的响应就退出等待
                                if "degrees" in line:
                                    break
                    
                    if response:
                        print("舵机反馈:")
                        print(response)
                    else:
                        print("警告: 没有收到舵机响应")
                else:
                    print("错误: 舵机号必须在1-4之间，角度必须在0-180之间")
            else:
                print("错误: 请输入有效的数字")
                
            # 等待一小段时间
            time.sleep(0.1)
            
    except serial.SerialException as e:
        print(f"串口错误: {e}")
        print(f"请确认设备已连接，并且COM端口号正确")
    except KeyboardInterrupt:
        print("\n程序已被用户中断")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("串口已关闭")

if __name__ == "__main__":
    main()