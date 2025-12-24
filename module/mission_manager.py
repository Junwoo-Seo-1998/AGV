from .context import RobotContext
from .states.tracking_state import LineTrackingState
from .states.approach_state import ApproachState
from .states.ocr_state import OCRCheckState
# [변경] 기존 GrabState 대신 PickupState import
from .states.pickup_state import PickupState

class MissionManager:
    def __init__(self, hardware, brain):
        self.context = RobotContext()
        self.hw = hardware
        
        self.states = {
            "TRACKING": LineTrackingState(hardware, brain),
            "APPROACH": ApproachState(hardware, brain),
            "OCR_CHECK": OCRCheckState(hardware),
            "PICKUP": PickupState(hardware), # 이름 변경 (PICKUP)
            "IDLE": None
        }
        self.current_state_name = "IDLE" 

    def set_state(self, state_name):
        # ... (기존 코드와 동일) ...
        old_state = self.states.get(self.current_state_name)
        if old_state and hasattr(old_state, 'on_exit'):
            old_state.on_exit(self.context)

        print(f"🔄 State Transition: {self.current_state_name} -> {state_name}")
        self.current_state_name = state_name

        new_state = self.states.get(state_name)
        if new_state:
            if hasattr(new_state, 'on_enter'):
                new_state.on_enter(self.context)
        
        if state_name == "IDLE": 
            self.hw.stop()

    def update(self):
        if self.current_state_name == "IDLE": return
        current_state = self.states.get(self.current_state_name)
        if current_state:
            next_state = current_state.process(self.context)
            if next_state: 
                self.set_state(next_state)