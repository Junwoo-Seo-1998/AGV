from jetbot import Robot, Camera
import time
import log.auto_logger
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

        if TTLServo:
            self.servo = TTLServo
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
        self.robot.left_motor.value = float(left)
        self.robot.right_motor.value = float(right)

    def stop(self):
        """주행만 정지 (카메라는 켜둠 - OCR 등을 위해)"""
        self.robot.stop()
        
    def rotate_camera(self, angle, servo_id):
        if self.servo:
            self.servo.servoAngleCtrl(servo_id, angle, 1, 100)
            time.sleep(1.0) # 회전 후 안정화 대기

    # [신규 추가] 프로그램 완전 종료 시 호출
    def close(self):
        """모터와 카메라를 모두 확실하게 정지 및 자원 해제"""
        self.stop() # 모터 정지
        if self.camera:
            self.camera.stop()
            print("📷 카메라 자원 해제 완료")
            
log.auto_logger.hook_agv_drive(AGVHardware)

