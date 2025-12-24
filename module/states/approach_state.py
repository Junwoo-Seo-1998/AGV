import numpy as np
from vision.color import ColorRecognizer

class ApproachState:
    def __init__(self, hardware, brain):
        self.hw = hardware
        self.brain = brain
        self.color_recognizer = ColorRecognizer()
        
        # [설정] 목표 위치
        self.STOP_Y_THRESHOLD = 200   # 이 값이 클수록 더 깊이 들어감 (최대 224)
        
        # [설정] 정렬 및 주행 튜닝
        self.BASE_SPEED = 0.15        # 정렬됐을 때의 최대 접근 속도 (매우 느림)
        self.ALIGNMENT_SENSITIVITY = 2.5 # 정렬 민감도 (클수록 조금만 틀어져도 멈칫함)
        
    def on_enter(self, context):
        print(f"⚠️ 정밀 접근 모드 진입 (Target Color: {context.last_detected_color})")
        self.hw.set_camera_resolution(224, 224)
        
    def process(self, context):
        # 해상도 설정
        #self.hw.set_camera_resolution(224, 224)
        image = self.hw.get_frame()
        if image is None: return None

        # ---------------------------------------------------------
        # 1. 정렬 우선 로직 (Alignment-First Logic)
        # ---------------------------------------------------------
        # 현재의 라인 오차(current_x)를 확인 (범위: -1.0 ~ 1.0, 0이 중앙)
        # 오차(error)가 클수록 속도(speed_gain)를 줄여서, 로봇이 전진하지 않고 방향만 틀게 유도함
        
        error = abs(context.current_x) # 절대값 오차
        
        # 속도 계산 공식: 기본속도 * (1 - 오차 * 민감도)
        # 예: 오차가 0이면 100% 속도, 오차가 0.4(민감도2.5 기준)면 속도 0
        dynamic_speed = self.BASE_SPEED * max(0.0, (1.0 - error * self.ALIGNMENT_SENSITIVITY))
        
        # Context의 속도 설정을 잠시 덮어씌움 (Brain이 이 값을 사용함)
        original_speed = context.speed_gain
        context.speed_gain = dynamic_speed

        # ---------------------------------------------------------
        # 2. 주행 계산 (Brain)
        # ---------------------------------------------------------
        # Brain은 설정된 낮은 속도와 현재 오차를 기반으로 모터 출력을 계산함
        left, right = self.brain.calculate(image, context)
        
        # 속도 복원 (다른 상태에 영향 주지 않기 위해)
        context.speed_gain = original_speed

        # ---------------------------------------------------------
        # 3. 타겟 확인 및 정지 판단
        # ---------------------------------------------------------
        color_res = self.color_recognizer.recognize(image)
        detected_y = color_res.center_y if color_res else 0
        
        # 디버깅: 현재 오차와 가변 속도 상태 확인
        # print(f"오차: {error:.2f} -> 속도: {dynamic_speed:.2f} | 타겟 Y: {detected_y}")

        # 목표 위치 도달 검사
        if color_res and detected_y >= self.STOP_Y_THRESHOLD:
            # (옵션) 도착은 했지만 정렬이 너무 안 되어 있다면(예: 0.2 이상) 
            # 멈추지 않고 미세하게 더 움직이게 할 수도 있으나, 
            # 위에서 이미 속도를 제어했으므로 도착 시점엔 대부분 정렬되어 있음.
            
            print(f"🛑 정렬된 상태로 도착 완료! (Y: {detected_y}, 오차: {context.current_x:.2f})")
            self.hw.stop()
            context.last_detected_color = color_res.color
            return "OCR_CHECK" # 다음 상태로 전환

        # ---------------------------------------------------------
        # 4. 구동
        # ---------------------------------------------------------
        self.hw.drive(left, right)
        return None