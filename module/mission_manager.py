from .context import RobotContext

# 분리한 모듈들을 import 합니다.
# (참고: module/states 폴더 안에 __init__.py를 만들어주세요)
from .states.tracking_state import LineTrackingState
from .states.ocr_state import OCRCheckState

class MissionManager:
    def __init__(self, hardware, brain):
        self.context = RobotContext()
        self.hw = hardware
        
        # 각 상태 클래스에 필요한 의존성을 주입하여 인스턴스 생성
        self.states = {
            "TRACKING": LineTrackingState(hardware, brain),
            "OCR_CHECK": OCRCheckState(hardware),
            "IDLE": None
        }
        self.current_state_name = "IDLE" 

    def set_state(self, state_name):
        print(f"🔄 State: {state_name}")
        self.current_state_name = state_name
        if state_name == "IDLE": self.hw.stop()

    def update(self):
        if self.current_state_name == "IDLE": return
        
        current_state = self.states.get(self.current_state_name)
        if current_state:
            next_state = current_state.process(self.context)
            if next_state: self.set_state(next_state)