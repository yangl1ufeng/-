import cv2
import os

# 创建目录用于保存图像
save_dir = "stereo_images"
os.makedirs(save_dir, exist_ok=True)
img_idx = 0

# 鼠标点击回调函数
def save_image(event, x, y, flags, param):
    global img_idx
    if event == cv2.EVENT_LBUTTONDOWN:  # 左键点击时触发保存
        ret, frame = param[0].read()
        if not ret:
            print("无法读取帧")
            return

        # 划分左右图像
        left = frame[:, :640]
        right = frame[:, 640:]

        # 保存图像
        cv2.imwrite(f"{save_dir}/left_{img_idx:02d}.png", left)
        cv2.imwrite(f"{save_dir}/right_{img_idx:02d}.png", right)
        print(f"已保存第 {img_idx} 组图像")
        img_idx += 1

# 初始化视频流
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

cv2.namedWindow("Stereo")
cv2.setMouseCallback("Stereo", save_image, param=(cap,))  # 设置鼠标回调

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # 划分左右图像
    left = frame[:, :640]
    right = frame[:, 640:]

    combined = cv2.hconcat([left, right])
    cv2.imshow("Stereo", combined)

    key = cv2.waitKey(1)
    if key == 27:  # 按下 'Esc' 键退出
        break

cap.release()
cv2.destroyAllWindows()
