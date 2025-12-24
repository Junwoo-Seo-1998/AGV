from jetbot import Robot, Camera
import time

# 서보 라이브러리 임포트 (없는 경우 예외처리)
try:
    from SCSCtrl import TTLServo
except ImportError:
    TTLServo = None
    print("⚠️ SCSCtrl 모듈을 찾을 수 없습니다. 서보 제어가 비활성화됩니다.")

class AGVHardware:
    def __init__(self):
        self.robot = Robot()
        try:
            self.camera = Camera.instance(width=816, height=616)
            print("✅ 하드웨어(카메라/모터) 연결 성공")
        except RuntimeError:
            print("⚠️ 카메라가 이미 사용 중이거나 연결되지 않았습니다.")
            self.camera = None

        # 서보 컨트롤러 초기화
        if TTLServo:
            self.servo = TTLServo
        else:
            self.servo = None

    def get_frame(self):
        if self.camera:
            return self.camera.value
        return None

    def drive(self, left, right):
        self.robot.left_motor.value = left
        self.robot.right_motor.value = right

    def stop(self):
        self.robot.stop()
        # 카메라는 계속 켜두어야 OCR이 가능하므로 camera.stop()은 호출하지 않음 (필요시 추가)
        
    def rotate_camera(self, angle, servo_id):
        """카메라를 지정된 각도로 회전 (OCRTask 코드 참조)"""
        if self.servo:
            self.servo.servoAngleCtrl(servo_id, angle, 1, 100)
            time.sleep(1.0) # 회전 후 안정화 대기