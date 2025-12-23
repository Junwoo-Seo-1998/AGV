# modules/hardware.py
import time
from jetbot import Robot, Camera
# SCSCtrl 라이브러리가 있다고 가정 (OCRTask.py 참조)
try:
    from SCSCtrl import TTLServo
except ImportError:
    TTLServo = None
    print("Warning: SCSCtrl module not found. Servo control disabled.")

class AGVHardware:
    def __init__(self):
        # 1. 구동부 (JetBot)
        self.robot = Robot()
        
        # 2. 비전 (Camera)
        try:
            self.camera = Camera.instance(width=224, height=224)
        except:
            self.camera = None
            
        # 3. 관절부 (Servo / IK)
        if TTLServo:
            self.servo = TTLServo()
        else:
            self.servo = None
            
        print("✅ 하드웨어 통합 초기화 완료")

    def get_frame(self):
        return self.camera.value if self.camera else None

    def drive(self, left, right):
        self.robot.left_motor.value = left
        self.robot.right_motor.value = right

    def stop(self):
        self.robot.stop()

    def move_servo(self, servo_id, angle, velocity=1, delay=0):
        """카메라 틸트/팬 또는 로봇팔 관절 제어"""
        if self.servo:
            # SCSCtrl 라이브러리 사용법에 맞춤
            self.servo.servoAngleCtrl(servo_id, angle, 1, velocity)
            if delay > 0:
                time.sleep(delay)

    def move_arm_ik(self, x, y, z):
        """
        [IK 로직] 역기구학을 계산하여 서보 각도를 제어하는 함수.
        실제 IK 수식이나 라이브러리 호출 코드를 여기에 작성하세요.
        """
        print(f"[HW] 로봇팔 이동 (IK): x={x}, y={y}, z={z}")
        # 예시:
        # angles = solve_inverse_kinematics(x, y, z)
        # self.move_servo(1, angles[0])
        # self.move_servo(2, angles[1])
        pass