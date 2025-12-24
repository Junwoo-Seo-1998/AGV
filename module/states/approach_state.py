# module/states/approach_state.py

from vision.color import ColorRecognizer

class ApproachState:
    def __init__(self, hardware, brain):
        self.hw = hardware
        self.brain = brain
        self.color_recognizer = ColorRecognizer()
        
        # [설정] 정지 목표 위치 (이미지 높이 224 기준)
        # 이 값이 클수록(224에 가까울수록) 로봇이 색상 위로 더 깊숙이 들어갑니다.
        # 카메라 각도에 따라 160~200 사이로 조절해보세요.
        self.STOP_Y_THRESHOLD = 180
        
        # 접근 속도 (평소보다 느리게)
        self.APPROACH_SPEED_FACTOR = 0.6 

    def process(self, context):
        self.hw.set_camera_resolution(224, 224)
        image = self.hw.get_frame()
        if image is None: return None

        # 1. 색상 위치 확인
        color_res = self.color_recognizer.recognize(image)
        
        # 색상을 놓쳤다면? 일단 직전 로직대로 천천히 전진하거나 멈추는 예외처리 필요
        # 여기서는 감지된 경우만 처리
        current_y = color_res.center_y if color_res else 0
        
        # 디버깅 출력 (좌표 확인용)
        if color_res:
            print(f"🎯 접근 중... 타겟 Y: {current_y} / 목표: {self.STOP_Y_THRESHOLD}")

        # 2. 정지 조건 검사 (목표 위치 도달 시)
        if color_res and current_y >= self.STOP_Y_THRESHOLD:
            print(f"🛑 정확한 위치 도착! (Y: {current_y}) -> OCR 시작")
            self.hw.stop()
            context.last_detected_color = color_res.color
            return "OCR_CHECK" # 정지 후 다음 상태로

        # 3. 목표에 도달하지 못했으면 라인 따라 천천히 접근
        left, right = self.brain.calculate(image, context)
        
        # 속도 감속 적용
        left = left * self.APPROACH_SPEED_FACTOR
        right = right * self.APPROACH_SPEED_FACTOR
        
        self.hw.drive(left, right)
        return None