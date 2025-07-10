#include <rtthread.h>
#include <rtdevice.h>
#include <stdlib.h>

/* 定义四个舵机的PWM设备及通道 */
#define SERVO1_PWM_DEV_NAME   "pwm2"  // 舵机1的PWM设备名称
#define SERVO1_PWM_DEV_CHANNEL 1      // 舵机1的PWM通道

#define SERVO2_PWM_DEV_NAME   "pwm2"  // 舵机2的PWM设备名称
#define SERVO2_PWM_DEV_CHANNEL 2      // 舵机2的PWM通道

#define SERVO3_PWM_DEV_NAME   "pwm2"  // 舵机3的PWM设备名称
#define SERVO3_PWM_DEV_CHANNEL 3      // 舵机3的PWM通道

#define SERVO4_PWM_DEV_NAME   "pwm2"  // 舵机4的PWM设备名称
#define SERVO4_PWM_DEV_CHANNEL 4      // 舵机4的PWM通道

struct rt_device_pwm *servo1_pwm_dev = RT_NULL; // 舵机1的PWM设备句柄
struct rt_device_pwm *servo2_pwm_dev = RT_NULL; // 舵机2的PWM设备句柄
struct rt_device_pwm *servo3_pwm_dev = RT_NULL; // 舵机3的PWM设备句柄
struct rt_device_pwm *servo4_pwm_dev = RT_NULL; // 舵机4的PWM设备句柄

/* PWM初始化函数 */
static int pwm_init(void)
{
    rt_uint32_t period = 20000000; // 周期20ms（单位：纳秒）
    rt_uint32_t pulse = 1500000;   // 初始脉宽1.5ms（90度）

    /* 查找并初始化四个舵机的PWM设备 */
    servo1_pwm_dev = (struct rt_device_pwm *)rt_device_find(SERVO1_PWM_DEV_NAME);
    if (!servo1_pwm_dev) { rt_kprintf("Error: Find SERVO1 failed!\n"); return -RT_ERROR; }
    rt_pwm_set(servo1_pwm_dev, SERVO1_PWM_DEV_CHANNEL, period, pulse);
    rt_pwm_enable(servo1_pwm_dev, SERVO1_PWM_DEV_CHANNEL);

    servo2_pwm_dev = (struct rt_device_pwm *)rt_device_find(SERVO2_PWM_DEV_NAME);
    if (!servo2_pwm_dev) { rt_kprintf("Error: Find SERVO2 failed!\n"); return -RT_ERROR; }
    rt_pwm_set(servo2_pwm_dev, SERVO2_PWM_DEV_CHANNEL, period, pulse);
    rt_pwm_enable(servo2_pwm_dev, SERVO2_PWM_DEV_CHANNEL);

    servo3_pwm_dev = (struct rt_device_pwm *)rt_device_find(SERVO3_PWM_DEV_NAME);
    if (!servo3_pwm_dev) { rt_kprintf("Error: Find SERVO3 failed!\n"); return -RT_ERROR; }
    rt_pwm_set(servo3_pwm_dev, SERVO3_PWM_DEV_CHANNEL, period, pulse);
    rt_pwm_enable(servo3_pwm_dev, SERVO3_PWM_DEV_CHANNEL);

    servo4_pwm_dev = (struct rt_device_pwm *)rt_device_find(SERVO4_PWM_DEV_NAME);
    if (!servo4_pwm_dev) { rt_kprintf("Error: Find SERVO4 failed!\n"); return -RT_ERROR; }
    rt_pwm_set(servo4_pwm_dev, SERVO4_PWM_DEV_CHANNEL, period, pulse);
    rt_pwm_enable(servo4_pwm_dev, SERVO4_PWM_DEV_CHANNEL);

    rt_kprintf("4 Servos initialized. Period:20ms, Initial pulse:1.5ms(90°)\n");
    return RT_EOK;
}

/* 设置舵机角度函数（0-180度） */
static int set_servo_angle(int argc, char *argv[])
{
    if (argc != 3)
    {
        rt_kprintf("Usage: set_angle [servo_id 1-4] [angle 0-180]\n");
        return RT_EOK;
    }

    int servo_id = atoi(argv[1]);
    int angle = atoi(argv[2]);

    if (angle < 0 || angle > 180)
    {
        rt_kprintf("Error: Angle out of range (0-180)!\n");
        return RT_EOK;
    }

    rt_uint32_t pulse = (angle * 2000000 / 180 + 500000);

    switch (servo_id)
    {
    case 1: if (servo1_pwm_dev) rt_pwm_set(servo1_pwm_dev, SERVO1_PWM_DEV_CHANNEL, 20000000, pulse); break;
    case 2: if (servo2_pwm_dev) rt_pwm_set(servo2_pwm_dev, SERVO2_PWM_DEV_CHANNEL, 20000000, pulse); break;
    case 3: if (servo3_pwm_dev) rt_pwm_set(servo3_pwm_dev, SERVO3_PWM_DEV_CHANNEL, 20000000, pulse); break;
    case 4: if (servo4_pwm_dev) rt_pwm_set(servo4_pwm_dev, SERVO4_PWM_DEV_CHANNEL, 20000000, pulse); break;
    default: rt_kprintf("Error: Invalid servo ID (1-4)!\n"); return RT_EOK;
    }

    rt_kprintf("Servo %d set to %d degrees (pulse: %d ns)\n", servo_id, angle, pulse);
    return RT_EOK;
}

/* 舵机测试线程 - 单线程控制四个舵机独立运动 */
static void servo_test_thread(void *parameter)
{
    struct {
        int angle;      // 当前角度
        int target;     // 目标角度
        int step;       // 步长
        int update_ms;  // 更新间隔(ms)
        rt_tick_t last_tick;
    } servo_state[4] = {
        {90, 0, -1, 20, 0},    // 舵机1：0-180度，20ms更新
        {90, 180, 2, 30, 0},   // 舵机2：90-180度，30ms更新
        {90, 45, -3, 40, 0},   // 舵机3：45-135度，40ms更新
        {90, 120, 4, 50, 0},   // 舵机4：60-120度，50ms更新
    };

    rt_kprintf("Starting 4-servo test...\n");

    while (1)
    {
        rt_tick_t now = rt_tick_get();

        for (int i = 0; i < 4; i++)
        {
            if (now - servo_state[i].last_tick >= rt_tick_from_millisecond(servo_state[i].update_ms))
            {
                servo_state[i].last_tick = now;
                servo_state[i].angle += servo_state[i].step;

                if ((servo_state[i].step > 0 && servo_state[i].angle >= servo_state[i].target) ||
                    (servo_state[i].step < 0 && servo_state[i].angle <= servo_state[i].target))
                {
                    servo_state[i].target = (servo_state[i].target == 0) ? 180 : 0;
                    servo_state[i].step = -servo_state[i].step;
                }

                if (servo_state[i].angle > 180) servo_state[i].angle = 180;
                if (servo_state[i].angle < 0) servo_state[i].angle = 0;

                rt_uint32_t pulse = (servo_state[i].angle * 2000000 / 180 + 500000);

                switch (i)
                {
                case 0: rt_pwm_set(servo1_pwm_dev, SERVO1_PWM_DEV_CHANNEL, 20000000, pulse); break;
                case 1: rt_pwm_set(servo2_pwm_dev, SERVO2_PWM_DEV_CHANNEL, 20000000, pulse); break;
                case 2: rt_pwm_set(servo3_pwm_dev, SERVO3_PWM_DEV_CHANNEL, 20000000, pulse); break;
                case 3: rt_pwm_set(servo4_pwm_dev, SERVO4_PWM_DEV_CHANNEL, 20000000, pulse); break;
                }

                rt_kprintf("Servo %d: %d° (pulse: %d ns)\n", i+1, servo_state[i].angle, pulse);
            }
        }

        rt_thread_mdelay(500);
    }
}

/* 启动测试线程的命令 */
static int start_servo_test(int argc, char *argv[])
{
    static rt_thread_t test_thread = RT_NULL;

    if (test_thread != RT_NULL)
    {
        rt_kprintf("Servo test is already running!\n");
        return RT_EOK;
    }

    test_thread = rt_thread_create("servo_test",
                                   servo_test_thread,
                                   RT_NULL,
                                   2048,      // 增大栈空间以支持四个舵机
                                   RT_THREAD_PRIORITY_MAX / 2,
                                   20);

    if (test_thread != RT_NULL)
    {
        rt_thread_startup(test_thread);
        rt_kprintf("4-servo test thread started!\n");
    }
    else
    {
        rt_kprintf("Failed to create servo test thread!\n");
    }

    return RT_EOK;
}

/* 添加平滑舵机移动功能 */
static int smooth_servo_move(int argc, char *argv[])
{
    if (argc != 4 && argc != 5)
    {
        rt_kprintf("Usage: smooth_move [servo_id 1-4] [target_angle 0-180] [step_size] [delay_ms]\n");
        return RT_EOK;
    }

    int servo_id = atoi(argv[1]);
    int target_angle = atoi(argv[2]);
    int step_size = atoi(argv[3]);
    int delay_ms = (argc == 5) ? atoi(argv[4]) : 30; // 默认延迟30ms

    if (target_angle < 0 || target_angle > 180)
    {
        rt_kprintf("Error: Target angle out of range (0-180)!\n");
        return RT_EOK;
    }

    // 平滑移动到目标角度
    int current_angle = 90; // 默认从90度开始
    int direction = (target_angle > current_angle) ? 1 : -1;

    rt_kprintf("Smoothly moving Servo %d to %d° (current: %d°)...\n", servo_id, target_angle, current_angle);

    while (current_angle != target_angle)
    {
        current_angle += direction * step_size;

        if ((direction > 0 && current_angle > target_angle) ||
            (direction < 0 && current_angle < target_angle))
        {
            current_angle = target_angle;
        }

        rt_uint32_t pulse = (current_angle * 2000000 / 180 + 500000);

        switch (servo_id)
        {
        case 1: if (servo1_pwm_dev) rt_pwm_set(servo1_pwm_dev, SERVO1_PWM_DEV_CHANNEL, 20000000, pulse); break;
        case 2: if (servo2_pwm_dev) rt_pwm_set(servo2_pwm_dev, SERVO2_PWM_DEV_CHANNEL, 20000000, pulse); break;
        case 3: if (servo3_pwm_dev) rt_pwm_set(servo3_pwm_dev, SERVO3_PWM_DEV_CHANNEL, 20000000, pulse); break;
        case 4: if (servo4_pwm_dev) rt_pwm_set(servo4_pwm_dev, SERVO4_PWM_DEV_CHANNEL, 20000000, pulse); break;
        default: rt_kprintf("Error: Invalid servo ID (1-4)!\n"); return RT_EOK;
        }

        rt_kprintf("  Servo %d: %d° (pulse: %d ns)\n", servo_id, current_angle, pulse);
        rt_thread_mdelay(delay_ms);
    }

    rt_kprintf("Servo %d has reached the target position: %d°\n", servo_id, target_angle);
    return RT_EOK;
}

/* 导出到MSH命令行 */
MSH_CMD_EXPORT(pwm_init, Initialize 4 servo PWM channels);
MSH_CMD_EXPORT(set_servo_angle, Set servo angle. Usage: set_angle [1-4] [0-180]);
MSH_CMD_EXPORT(start_servo_test, Start 4-servo test with different motions);
MSH_CMD_EXPORT(smooth_servo_move, Smoothly move servo to target angle. Usage: smooth_move [1-4] [0-180] [step_size] [delay_ms]);

INIT_APP_EXPORT(pwm_init);
