@echo off
echo ======================================
echo 智能机器臂喂食控制系统
echo ======================================
echo.
echo 正在启动应用程序...
echo.

cd /d "%~dp0"

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python
    pause
    exit /b 1
)

REM 检查必要的模块
echo 检查依赖模块...
python -c "import cv2, mediapipe, serial, numpy, tkinter" >nul 2>&1
if errorlevel 1 (
    echo 警告: 缺少必要的模块，正在尝试安装...
    pip install opencv-python mediapipe pyserial numpy
)

REM 启动增强版应用程序
echo.
echo 启动智能喂食控制应用程序...
python app_launcher.py

if errorlevel 1 (
    echo.
    echo 应用程序启动失败，尝试启动终端版本...
    python calculate_angle.py
    pause
)
