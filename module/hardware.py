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
            # 초기 해상도는 224x224로 시작하지만, state에서 변경 가능
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

    def set_camera_resolution(self, width, height):
        """
        카메라 해상도를 동적으로 변경합니다.
        현재 해상도와 다를 경우에만 카메라를 재시작합니다.
        """
        if self.camera is None:
            return

        # 현재 설정과 동일하면 변경하지 않음 (불필요한 딜레이 방지)
        if self.camera.width == width and self.camera.height == height:
            return

        print(f"🔄 카메라 해상도 변경: {self.camera.width}x{self.camera.height} -> {width}x{height}")
        
        # 카메라 정지 후 설정 변경 및 재시작
        self.camera.stop()
        self.camera.width = width
        self.camera.height = height
        self.camera.start()
        
        # 카메라 재시작 후 이미지가 안정화될 때까지 잠시 대기
        time.sleep(0.5)

    def drive(self, left, right):
        self.robot.left_motor.value = left
        self.robot.right_motor.value = right

    def stop(self):
        self.robot.stop()
        # 카메라는 계속 켜두어야 OCR이 가능하므로 camera.stop()은 호출하지 않음
        
    def rotate_camera(self, angle, servo_id):
        """카메라를 지정된 각도로 회전 (OCRTask 코드 참조)"""
        if self.servo:
            self.servo.servoAngleCtrl(servo_id, angle, 1, 100)
            time.sleep(1.0) # 회전 후 안정화 대기