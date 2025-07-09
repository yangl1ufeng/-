
import cv2
import numpy as np

# -----------------------------------双目相机的基本参数---------------------------------------------------------
#   left_camera_matrix          左相机的内参矩阵
#   right_camera_matrix         右相机的内参矩阵
#
#   left_distortion             左相机的畸变系数    格式(K1,K2,P1,P2,0)
#   right_distortion            右相机的畸变系数
# -------------------------------------------------------------------------------------------------------------
# 左镜头的内参，如焦距
left_camera_matrix = np.array([[1.28782208e+03, 0.00000000e+00, 1.63925648e+02],
                               [0.00000000e+00, 1.30509164e+03, 2.13901456e+02],
                               [0.00000000e+00, 0.00000000e+00, 1.00000000e+00]])
right_camera_matrix = np.array([[ 1.23753925e+03,  0.00000000e+00, -1.15126361e+01],
 [ 0.00000000e+00,  1.29207405e+03,  2.28432426e+02],
 [ 0.00000000e+00,  0.00000000e+00,  1.00000000e+00]])
 

# 畸变系数,K1、K2、K3为径向畸变,P1、P2为切向畸变
left_distortion = np.array([[ 6.73438062e-01, -1.24494025e+01, -2.86825939e-02, 1.67518823e-02, 5.00656930e+01]])
right_distortion = np.array([[ 0.2429477,  -5.29792274, -0.03965634,  0.0402608,  15.50194529]])
# 旋转矩阵
R = np.array([[0.99031455, 0.00344004, 0.13879936],
                            [-0.00305175, 0.99999081, -0.00301023],
                            [-0.13880844, 0.00255749, 0.99031595]])
# 平移矩阵
T =  np.array([[-61.22409065], [ -4.82093845], [  5.65538616]])
size = (640, 480)

R1, R2, P1, P2, Q, validPixROI1, validPixROI2 = cv2.stereoRectify(left_camera_matrix, left_distortion,
                                                                  right_camera_matrix, right_distortion, size, R,
                                                                  T)

# 校正查找映射表,将原始图像和校正后的图像上的点一一对应起来
left_map1, left_map2 = cv2.initUndistortRectifyMap(left_camera_matrix, left_distortion, R1, P1, size, cv2.CV_16SC2)
right_map1, right_map2 = cv2.initUndistortRectifyMap(right_camera_matrix, right_distortion, R2, P2, size, cv2.CV_16SC2)
print(Q)
