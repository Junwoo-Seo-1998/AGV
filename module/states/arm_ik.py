import time
from .base_state import BaseState

class ArmIKState(BaseState):
    def __init__(self, hardware):
        self.hw = hardware

    def process(self, context):
        print("[State] 로봇팔 작업 시작")
        
        # Context에 저장된 OCR 결과에 따라 동작 분기 가능
        target_text = context.ocr_result
        print(f"   -> 타겟 물체 정보: {target_text}")

        # 1. 접근 (IK 이동)
        self.hw.move_arm_ik(10, 0, 5) # 예: (x=10, y=0, z=5)
        time.sleep(1)
        
        # 2. 집기 (그리퍼 동작 등)
        # self.hw.move_servo(gripper_id, close_angle)
        time.sleep(1)
        
        # 3. 원위치
        self.hw.move_arm_ik(0, 0, 10)
        time.sleep(1)
        
        print("   -> 로봇팔 작업 완료")
        
        context.is_mission_completed = True # 중복 수행 방지
        return "TRACKING" # 다시 주행 복귀