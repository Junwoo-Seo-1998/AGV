import numpy as np
from vision.color import ColorRecognizer

class ApproachState:
    def __init__(self, hardware, brain):
        self.hw = hardware
        self.brain = brain
        self.color_recognizer = ColorRecognizer()
        
        self.STOP_Y_THRESHOLD = 180   # 정지 목표 위치
        self.BASE_SPEED = 0.15        # 접근 기본 속도
        self.ALIGNMENT_SENSITIVITY = 2.0 

    def on_enter(self, context):
        print(f"⚠️ 정밀 접근 모드 진입 (Target: {context.last_detected_color})")
        self.hw.set_camera_resolution(224, 224)

    def process(self, context):
        image = self.hw.get_frame()
        if image is None: return None

        # 1. 색상 인식
        color_res = self.color_recognizer.recognize(image)
        
        # [핵심 수정] 타겟 소실 시 트래킹으로 복귀
        # 색상이 아예 안 보이거나(None), 
        # 혹은 지금 보고 있는 색이 우리가 쫓던 색(last_detected_color)이 아니라면?
        if not color_res:
            print(f"💨 타겟 소실! (색상 없음) -> 일반 주행으로 복귀")
            return "TRACKING"
            
        # (옵션) 색상은 있는데 다른 색이라면? -> 상황에 따라 주석 처리 가능
        if color_res.color != context.last_detected_color:
            print(f"🤔 색상 변경됨 ({context.last_detected_color} -> {color_res.color}) -> 재판단 위해 복귀")
            return "TRACKING"

        # 2. 목표 위치 도달 확인
        detected_y = color_res.center_y
        if detected_y >= self.STOP_Y_THRESHOLD:
            print(f"🛑 정위치 도착 (Y: {detected_y}) -> OCR 시작")
            self.hw.stop()
            return "OCR_CHECK"

        # 3. 정렬 및 주행 (가변 속도)
        error = abs(context.current_x)
        dynamic_speed = self.BASE_SPEED * max(0.0, (1.0 - error * self.ALIGNMENT_SENSITIVITY))
        
        original_speed = context.speed_gain
        context.speed_gain = dynamic_speed
        
        left, right = self.brain.calculate(image, context)
        context.speed_gain = original_speed # 복구
        
        self.hw.drive(left, right)
        return None