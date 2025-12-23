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
            self.camera = Camera.instance(width=224, height=224)
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
        if self.servo:
            self.servo.servoAngleCtrl(servo_id, angle, 1, 100)
            time.sleep(1.0) # 회전 후 안정화 대기

    # [추가] 짐 집기 동작 (toy_clearner 로직 이식) -> 이거는 실제로 코드 실행 해봐야 할듯 내일 일찍 가서
    def arm_grab(self):
        print("🦾 [HW] 짐 잡기 동작 시작")
        if self.servo:
            # 1. 팔 내리기 (좌표 제어 예시)
            self.servo.xyInput(200, -90)
            time.sleep(1.5)
            # 2. 그리퍼 닫기 (ID:4, Angle:40)
            self.servo.servoAngleCtrl(4, 40, -1, 150)
            time.sleep(1.5)
            # 3. 팔 들어올리기 (주행 자세)
            self.servo.servoAngleCtrl(2, 0, 1, 200)
            self.servo.servoAngleCtrl(3, 0, 1, 200)
            time.sleep(1.5)
        return True
    
    # [추가] 짐 놓기 동작
    def arm_release(self):
        print("🦾 [HW] 짐 놓기 동작 시작")
        if self.servo:
            # 1. 팔 내리기
            self.servo.xyInput(200, -90)
            time.sleep(1.5)
            # 2. 그리퍼 열기 (ID:4, Angle:100)
            self.servo.servoAngleCtrl(4, 100, 1, 150)
            time.sleep(1.5)
            # 3. 팔 원위치
            self.servo.servoAngleCtrl(2, 0, 1, 200)
            self.servo.servoAngleCtrl(3, 0, 1, 200)
            time.sleep(1.0)