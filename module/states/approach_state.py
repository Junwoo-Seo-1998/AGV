import time
import numpy as np
from vision.color import ColorRecognizer

class ApproachState:
    def __init__(self, hardware, brain):
        self.hw = hardware
        self.brain = brain
        self.color_recognizer = ColorRecognizer()
        
        # [설정] 정지 판정 기준
        self.STOP_Y_THRESHOLD = 190   # 화면 거의 끝까지 볼 때까지 대기
        self.OVERRUN_TIME = 0.8       # [중요] 도착 판정 후 더 밀고 들어가는 시간 (초)
        
        # 주행 관련 설정
        self.BASE_SPEED = 0.2         
        self.MIN_MOVE_SPEED = 0.13    
        self.ALIGNMENT_SENSITIVITY = 2.0 
        
        self.last_known_y = 0

    def on_enter(self, context):
        print(f"⚠️ 정밀 접근 모드 진입 (Target: {context.last_detected_color})")
        self.hw.set_camera_resolution(224, 224)
        self.last_known_y = 0

    # 도착 시 실행할 '마무리 전진' 함수
    def finish_approach(self, context, reason):
        print(f"🏁 {reason} -> ⏱️ {self.OVERRUN_TIME}초간 추가 전진하여 올라탑니다!")
        
        # 정렬된 상태로 직진 (속도는 조금 낮춰서 안전하게)
        self.hw.drive(0.15, 0.15)
        time.sleep(self.OVERRUN_TIME)
        
        self.hw.stop()
        print("🛑 완전히 정지했습니다. OCR을 시작합니다.")
        return "OCR_CHECK"

    def process(self, context):
        image = self.hw.get_frame()
        if image is None: return None

        color_res = self.color_recognizer.recognize(image)
        
        # 1. 타겟 소실 처리
        if not color_res:
            # 타겟이 화면 하단(150px 이상)에서 사라졌다면 -> "도착해서 로봇 밑으로 들어간 것"
            if self.last_known_y > 150:
                return self.finish_approach(context, reason=f"타겟 하단 진입 (Last Y: {self.last_known_y})")
            else:
                print(f"💨 타겟 소실 (Last Y: {self.last_known_y}) -> 일반 주행 복귀")
                return "TRACKING"

        # 2. 다른 색이면 복귀
        if color_res.color != context.last_detected_color:
             return "TRACKING"

        # 3. 목표 도달 확인 (화면에 보일 때)
        self.last_known_y = color_res.center_y
        if self.last_known_y >= self.STOP_Y_THRESHOLD:
            return self.finish_approach(context, reason=f"정위치 도달 (Visible Y: {self.last_known_y})")

        # 4. 주행 로직 (최소 속도 보장)
        error = abs(context.current_x)
        calculated_speed = self.BASE_SPEED * max(0.0, (1.0 - error * self.ALIGNMENT_SENSITIVITY))
        
        if calculated_speed > 0.01: 
            dynamic_speed = max(calculated_speed, self.MIN_MOVE_SPEED)
        else:
            dynamic_speed = 0.0

        original_speed = context.speed_gain
        context.speed_gain = dynamic_speed
        
        left, right = self.brain.calculate(image, context)
        context.speed_gain = original_speed
        
        self.hw.drive(left, right)
        return None