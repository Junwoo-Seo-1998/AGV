from jetbot import Robot, Camera
import time

try:
    from SCSCtrl import TTLServo
except ImportError:
    TTLServo = None
    print("⚠️ SCSCtrl 모듈을 찾을 수 없습니다.")

class AGVHardware:
    def __init__(self):
        self.robot = Robot()
        try:
            self.camera = Camera.instance(width=224, height=224)
        except RuntimeError:
            self.camera = None

        if TTLServo:
            self.servo = TTLServo
            # 초기 팔 위치 설정
            self.servo.servoAngleCtrl(2, 0, 1, 150)
            self.servo.servoAngleCtrl(3, 0, 1, 150)
            self.servo.servoAngleCtrl(4, 100, 1, 150) # 열기
        else:
            self.servo = None

    def get_frame(self):
        return self.camera.value if self.camera else None

    # [수정] 카메라 해상도 변경 기능
    def set_camera_resolution(self, width, height):
        if self.camera is None: return
        if self.camera.width == width and self.camera.height == height: return
        self.camera.stop()
        self.camera.width = width
        self.camera.height = height
        self.camera.start()
        time.sleep(0.5)

    def drive(self, left, right):
        self.robot.left_motor.value = left
        self.robot.right_motor.value = right

    def stop(self):
        self.robot.stop()

    # [요청하신 Grab 함수 구현]
    def grab_sequence(self):
        if not self.servo: return

        print("🦾 [GRAB] 물체 집기 시작")
        
        # 1. Position arm down
        self.servo.xyInput(200, -90)
        time.sleep(1)
        
        # 2. Close grip
        self.servo.servoAngleCtrl(4, 40, -1, 150)
        time.sleep(2) # (5초는 너무 길어서 2초로 조정, 필요시 5로 변경)
        
        # 3. PLACE IN BASKET (Position arm at back)
        self.servo.servoAngleCtrl(2, 100, -1, 200)
        self.servo.servoAngleCtrl(3, 100, 1, 200)
        time.sleep(3) # (5초 -> 3초)
        
        # 4. Open grip
        self.servo.servoAngleCtrl(4, 100, 1, 150)
        time.sleep(1) # (3초 -> 1초)
        
        # 5. Position arm at initial position
        self.servo.servoAngleCtrl(2, 0, 1, 200)
        self.servo.servoAngleCtrl(3, 0, 1, 200)
        time.sleep(2)
        
        print("✅ [GRAB] 완료")