import cv2
import numpy as np

# 设置棋盘格的大小
chessboard_size = (7, 7)  # 7x7 棋盘格

# 每个格子的像素大小
square_size = 50  # 格子边长，单位为像素

# 创建一个黑白棋盘格
board = np.zeros((chessboard_size[1] * square_size, chessboard_size[0] * square_size), dtype=np.uint8)

# 填充棋盘格
for row in range(chessboard_size[1]):
    for col in range(chessboard_size[0]):
        if (row + col) % 2 == 0:  # 奇偶数位置填充白色
            board[row * square_size : (row + 1) * square_size, col * square_size : (col + 1) * square_size] = 255

# 显示棋盘格
cv2.imshow('Chessboard', board)
cv2.waitKey(0)
cv2.destroyAllWindows()

# 保存棋盘格图像
cv2.imwrite('chessboard_7x7.png', board)
