import numpy as np
from vision.color import ColorRecognizer

class ApproachState:
    def __init__(self, hardware, brain):
        self.hw = hardware
        self.brain = brain
        self.color_recognizer = ColorRecognizer()
        
        self.STOP_Y_THRESHOLD = 180
        self.BASE_SPEED = 0.2         # [상향] 기본 속도를 조금 높임 (0.15 -> 0.2)
        self.ALIGNMENT_SENSITIVITY = 2.0 
        
        # [신규] 모터가 움직일 수 있는 최소 힘 (하드웨어마다 다르지만 보통 0.12~0.15)
        self.MIN_MOVE_SPEED = 0.13    
        
        self.last_known_y = 0

    def on_enter(self, context):
        print(f"⚠️ 정밀 접근 모드 진입 (Target: {context.last_detected_color})")
        self.hw.set_camera_resolution(224, 224)
        self.last_known_y = 0

    def process(self, context):
        image = self.hw.get_frame()
        if image is None: return None

        color_res = self.color_recognizer.recognize(image)
        
        # 1. 타겟 소실 처리 (도착 or 복귀)
        if not color_res:
            if self.last_known_y > 150:
                print(f"📉 타겟 하단 통과 (Last Y: {self.last_known_y}) -> 도착 간주")
                self.hw.stop()
                return "OCR_CHECK"
            else:
                print(f"💨 타겟 소실 -> 일반 주행 복귀")
                return "TRACKING"

        # 2. 다른 색이면 복귀
        if color_res.color != context.last_detected_color:
             return "TRACKING"

        # 3. 목표 도달 확인
        self.last_known_y = color_res.center_y
        if self.last_known_y >= self.STOP_Y_THRESHOLD:
            print(f"🛑 정위치 도착 (Visible Y: {self.last_known_y}) -> OCR 시작")
            self.hw.stop()
            return "OCR_CHECK"

        # 4. [핵심 수정] 주행 속도 계산 (최소 속도 클램핑)
        error = abs(context.current_x)
        
        # 가변 속도 계산
        calculated_speed = self.BASE_SPEED * max(0.0, (1.0 - error * self.ALIGNMENT_SENSITIVITY))
        
        # [수정] 속도가 0(제자리 회전)이 아니라면, 최소한 움직일 힘은 줘야 함
        if calculated_speed > 0.01: 
            dynamic_speed = max(calculated_speed, self.MIN_MOVE_SPEED)
        else:
            dynamic_speed = 0.0 # 오차가 너무 크면 제자리 회전

        # 속도 적용
        original_speed = context.speed_gain
        context.speed_gain = dynamic_speed
        
        left, right = self.brain.calculate(image, context)
        context.speed_gain = original_speed
        
        self.hw.drive(left, right)
        return None