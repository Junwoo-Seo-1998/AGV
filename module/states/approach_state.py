import time
import numpy as np
from vision.color import ColorRecognizer

class ApproachState:
    def __init__(self, hardware, brain):
        self.hw = hardware
        self.brain = brain
        self.color_recognizer = ColorRecognizer()
        
        # [설정]
        self.STOP_Y_THRESHOLD = 190
        self.OVERRUN_TIME = 0.8       # 추가 전진 시간
        
        self.BASE_SPEED = 0.2         
        self.MIN_MOVE_SPEED = 0.13    
        self.ALIGNMENT_SENSITIVITY = 2.0 
        
        self.last_known_y = 0

    def on_enter(self, context):
        print(f"⚠️ 정밀 접근 모드 진입 (Target: {context.last_detected_color})")
        self.hw.set_camera_resolution(224, 224)
        self.last_known_y = 0

    # [핵심 수정] 오버런 중에도 라인을 보면서 주행
    def finish_approach(self, context, reason):
        print(f"🏁 {reason} -> ⏱️ {self.OVERRUN_TIME}초간 라인 유지하며 진입!")
        
        start_time = time.time()
        
        # 오버런 전용 속도 (천천히, 신중하게)
        overrun_speed = 0.15  
        
        # 기존 속도 백업
        original_speed = context.speed_gain
        context.speed_gain = overrun_speed

        # 정해진 시간 동안 반복문 실행
        while time.time() - start_time < self.OVERRUN_TIME:
            # 1. 이미지 캡처
            image = self.hw.get_frame()
            if image is None: continue
            
            # 2. 라인 트래킹 계산 (Brain 사용) - 색상 무시, 라인만 추적
            left, right = self.brain.calculate(image, context)
            
            # 3. 구동
            self.hw.drive(left, right)
            
            time.sleep(0.01)
        
        # 속도 복구 및 정지
        context.speed_gain = original_speed
        self.hw.stop()
        
        print("🛑 오버런 완료. 정지했습니다.")
        
        # [여기가 수정된 부분입니다]
        # 오렌지색이면 물체 수거(PICKUP) 모드로, 아니면 OCR 모드로 이동
        if context.last_detected_color == 'orange':
            print("👉 오렌지색(짐 수거) 감지 -> PICKUP 상태로 전환")
            return "PICKUP"
        else:
            print("👉 배송지 도착 -> OCR_CHECK 상태로 전환")
            return "OCR_CHECK"

    def process(self, context):
        image = self.hw.get_frame()
        if image is None: return None

        color_res = self.color_recognizer.recognize(image)
        
        # 1. 타겟 소실 (도착 판단)
        if not color_res:
            if self.last_known_y > 150:
                return self.finish_approach(context, reason=f"타겟 하단 통과 (Last Y: {self.last_known_y})")
            else:
                print(f"💨 타겟 소실 -> 일반 주행 복귀")
                return "TRACKING"

        # 2. 색상 검증
        if color_res.color != context.last_detected_color:
             return "TRACKING"

        # 3. 목표 도달 확인 (보이는 상태)
        self.last_known_y = color_res.center_y
        if self.last_known_y >= self.STOP_Y_THRESHOLD:
            return self.finish_approach(context, reason=f"정위치 도달 (Visible Y: {self.last_known_y})")

        # 4. 접근 주행 (가변 속도)
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