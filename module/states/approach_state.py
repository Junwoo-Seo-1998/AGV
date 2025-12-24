import numpy as np
from vision.color import ColorRecognizer

class ApproachState:
    def __init__(self, hardware, brain):
        self.hw = hardware
        self.brain = brain
        self.color_recognizer = ColorRecognizer()
        
        self.STOP_Y_THRESHOLD = 180   # 안전하게 멈추는 기준선
        self.BASE_SPEED = 0.15
        self.ALIGNMENT_SENSITIVITY = 2.0 
        
        # [신규] 마지막 위치 기억용 변수
        self.last_known_y = 0

    def on_enter(self, context):
        print(f"⚠️ 정밀 접근 모드 진입 (Target: {context.last_detected_color})")
        self.hw.set_camera_resolution(224, 224)
        self.last_known_y = 0 # 초기화

    def process(self, context):
        image = self.hw.get_frame()
        if image is None: return None

        color_res = self.color_recognizer.recognize(image)
        
        # -----------------------------------------------------------
        # 1. 색상을 놓쳤을 때 (사라짐) 처리
        # -----------------------------------------------------------
        if not color_res:
            # (A) 바로 밑(하단)에서 사라진 경우 -> "도착 완료"로 판단
            # 예: 마지막 위치가 150 이상이었다면, 로봇 밑으로 들어간 것임
            if self.last_known_y > 150:
                print(f"📉 타겟이 하단으로 진입함 (Last Y: {self.last_known_y}) -> 도착 간주")
                self.hw.stop()
                return "OCR_CHECK"
            
            # (B) 멀리서 사라지거나 엉뚱한 경우 -> "주행 복귀"
            else:
                print(f"💨 타겟 소실 (Last Y: {self.last_known_y}) -> 일반 주행 복귀")
                return "TRACKING"

        # -----------------------------------------------------------
        # 2. 색상이 보일 때 처리
        # -----------------------------------------------------------
        # 다른 색이면 복귀 (오인식 방지)
        if color_res.color != context.last_detected_color:
             return "TRACKING"

        # 현재 위치 갱신
        self.last_known_y = color_res.center_y
        
        # 목표 위치 도달 확인 (보이는 상태에서 도달)
        if self.last_known_y >= self.STOP_Y_THRESHOLD:
            print(f"🛑 정위치 도착 (Visible Y: {self.last_known_y}) -> OCR 시작")
            self.hw.stop()
            return "OCR_CHECK"

        # -----------------------------------------------------------
        # 3. 주행 로직 (정렬 및 접근)
        # -----------------------------------------------------------
        error = abs(context.current_x)
        dynamic_speed = self.BASE_SPEED * max(0.0, (1.0 - error * self.ALIGNMENT_SENSITIVITY))
        
        original_speed = context.speed_gain
        context.speed_gain = dynamic_speed
        
        left, right = self.brain.calculate(image, context)
        context.speed_gain = original_speed
        
        self.hw.drive(left, right)
        return None