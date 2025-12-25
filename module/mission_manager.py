from .context import RobotContext

# 분리한 모듈들을 import 합니다.
# (참고: module/states 폴더 안에 __init__.py를 만들어주세요)
from .states.tracking_state import LineTrackingState
from .states.ocr_state import OCRCheckState
from .states.find_target_state import FindTargetState
from .states.approach_state import ApproachState

class MissionManager:
    def __init__(self, hardware, brain):
        self.context = RobotContext()
        self.hw = hardware
        
        # 각 상태 클래스에 필요한 의존성을 주입하여 인스턴스 생성
        self.states = {
            "TRACKING": LineTrackingState(hardware, brain),
            "OCR_CHECK": OCRCheckState(hardware),
            "APPROACH": ApproachState(hardware, brain),
            "FIND_TARGET": FindTargetState(hardware),
            "IDLE": None
        }
        self.current_state_name = "IDLE" 

    def set_state(self, state_name):
        # 1. 이전 상태의 종료 함수(on_exit) 호출
        old_state = self.states.get(self.current_state_name)
        if old_state and hasattr(old_state, 'on_exit'):
            old_state.on_exit(self.context)

        print(f"🔄 State Transition: {self.current_state_name} -> {state_name}")
        self.current_state_name = state_name

        # 2. 새로운 상태의 진입 함수(on_enter) 호출
        new_state = self.states.get(state_name)
        if new_state:
            if hasattr(new_state, 'on_enter'):
                new_state.on_enter(self.context)
        
        # IDLE일 경우 즉시 정지
        if state_name == "IDLE": 
            self.hw.stop()

    def update(self):
        if self.current_state_name == "IDLE": return
        
        current_state = self.states.get(self.current_state_name)
        if current_state:
            # 상태의 process 실행 후, 반환값이 있으면 상태 변경
            next_state = current_state.process(self.context)
            if next_state: 
                self.set_state(next_state)