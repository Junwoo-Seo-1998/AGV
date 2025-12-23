from jetbot import Robot, Camera

class AGVHardware:
    def __init__(self):
        self.robot = Robot()
        try:
            # 카메라는 싱글톤이라 instance()로 호출
            self.camera = Camera.instance(width=224, height=224)
            print("✅ 하드웨어(카메라/모터) 연결 성공")
        except RuntimeError:
            print("⚠️ 카메라가 이미 사용 중이거나 연결되지 않았습니다.")
            self.camera = None

    def get_frame(self):
        if self.camera:
            return self.camera.value
        return None

    def drive(self, left, right):
        self.robot.left_motor.value = left
        self.robot.right_motor.value = right

    def stop(self):
        self.robot.stop()