from .context import RobotContext
from .states.tracking import LineTrackingState
from .states.ocr import OCRState
from .states.arm_ik import ArmIKState

class MissionManager:
    def __init__(self, hardware, brain, ocr_detector, map1, map2):
        self.context = RobotContext()
        self.hw = hardware
        
        # 상태 등록 (모든 의존성을 여기서 주입)
        self.states = {
            "IDLE": None,
            "TRACKING": LineTrackingState(hardware, brain),
            "OCR": OCRState(hardware, ocr_detector, map1, map2),
            "ARM_IK": ArmIKState(hardware)
        }
        
        self.current_state_name = "IDLE" 

    def set_state(self, state_name):
        print(f"🔄 State Change: {self.current_state_name} -> {state_name}")
        self.current_state_name = state_name
        
        if state_name == "IDLE":
            self.hw.stop()

    def update(self):
        """메인 루프에서 주기적으로 호출"""
        if self.current_state_name == "IDLE":
            return

        current_state = self.states.get(self.current_state_name)
        if current_state:
            # 상태 실행 후 다음 상태(next_state)를 받아옴
            next_state = current_state.process(self.context)
            
            # 상태 전환 요청이 있으면 변경
            if next_state:
                self.set_state(next_state)