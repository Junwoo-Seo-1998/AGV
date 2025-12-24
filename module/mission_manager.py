from .context import RobotContext

# 상태 클래스들 import
from .states.tracking_state import LineTrackingState
from .states.approach_state import ApproachState
from .states.ocr_state import OCRCheckState
from .states.pickup_state import PickupState

import log.auto_logger
class MissionManager:
    def __init__(self, hardware, brain):
        self.context = RobotContext()
        self.hw = hardware
        
        # 각 상태 클래스 인스턴스 생성
        self.states = {
            "TRACKING": LineTrackingState(hardware, brain),
            "APPROACH": ApproachState(hardware, brain),
            "OCR_CHECK": OCRCheckState(hardware),
            "PICKUP": PickupState(hardware), # 이름 변경 (PICKUP)
            "IDLE": None
        }
        # [핵심] 모든 State의 'process' 함수에 '도청 장치(Verbose Hook)' 설치
        print(">>> [MissionManager] Hooking state processes for GUI logging...")
        for name, state_obj in self.states.items():
            if state_obj and hasattr(state_obj, 'process'):
                # process 메서드를 'print 가로채기' 버전으로 교체
                state_obj.process = log.auto_logger.make_verbose(state_obj.process)

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