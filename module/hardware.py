from jetbot import Robot, Camera
import time

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

        if TTLServo:
            self.servo = TTLServo
            # 초기화: 팔을 안전한 위치(Up)로 이동 & 그리퍼 열기
            self.servo.servoAngleCtrl(2, 0, 1, 150)
            self.servo.servoAngleCtrl(3, 0, 1, 150)
            self.servo.servoAngleCtrl(4, 100, 1, 150) 
        else:
            self.servo = None

    def get_frame(self):
        if self.camera:
            return self.camera.value
        return None

    def set_camera_resolution(self, width, height):
        if self.camera is None: return
        if self.camera.width == width and self.camera.height == height: return

        print(f"🔄 카메라 해상도 변경: {self.camera.width}x{self.camera.height} -> {width}x{height}")
        self.camera.stop()
        self.camera.width = width
        self.camera.height = height
        self.camera.start()
        time.sleep(0.5)

    def drive(self, left, right):
        self.robot.left_motor.value = left
        self.robot.right_motor.value = right

    def stop(self):
        """주행만 정지 (카메라는 켜둠)"""
        self.robot.stop()
        
    def rotate_camera(self, angle, servo_id):
        if self.servo:
            # servoAngleCtrl(ID, Angle, Speed, Direction)
            # 기존 코드: self.servo.servoAngleCtrl(servo_id, angle, 1, 100)
            self.servo.servoAngleCtrl(servo_id, angle, 1, 500)
            time.sleep(1.0)

    # [신규 추가] 짐 수거(Grab) 시퀀스
    def grab_sequence(self):
        if not self.servo:
            print("⚠️ 서보 모터가 연결되지 않았습니다.")
            return

        print("🦾 [GRAB] 물체 수거를 시작합니다...")
        
        # 1. 팔을 내려서 물체 위치로 이동 (GRAB Position)
        # xyInput: toy_clearner 값 (200, -90)
        self.servo.xyInput(200, -90)
        time.sleep(1.5)
        
        # 2. 그리퍼 닫기 (물체 잡기)
        # ID 4, Angle 40 (Close)
        self.servo.servoAngleCtrl(4, 40, -1, 150)
        time.sleep(1.0)
        
        print("📦 [GRAB] 물체 획득! 바구니로 이동합니다.")

        # 3. 바구니로 이동 (PLACE IN BASKET)
        # ID 2, 3번을 100도로 이동하여 뒤로 젖힘
        self.servo.servoAngleCtrl(2, 100, -1, 200)
        self.servo.servoAngleCtrl(3, 100, 1, 200)
        time.sleep(3.0) # 팔이 뒤로 넘어가는 시간
        
        # 4. 그리퍼 열기 (떨구기)
        self.servo.servoAngleCtrl(4, 100, 1, 150)
        time.sleep(1.0)
        
        # 5. 팔 원위치 (Initial Position)
        self.servo.servoAngleCtrl(2, 0, 1, 200)
        self.servo.servoAngleCtrl(3, 0, 1, 200)
        time.sleep(1.5)
        
        print("✅ [GRAB] 수거 완료.")