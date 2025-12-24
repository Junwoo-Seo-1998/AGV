# module/mission_manager.py

class MissionManager:
    def __init__(self, hardware, brain):
        self.context = RobotContext()
        self.hw = hardware
        
        # 상태 초기화 (여기서는 인스턴스만 생성)
        self.states = {
            "TRACKING": LineTrackingState(hardware, brain),
            "APPROACH": ApproachState(hardware, brain),
            "OCR_CHECK": OCRCheckState(hardware),
            "IDLE": None
        }
        self.current_state_name = "IDLE" 

    def set_state(self, state_name):
        # 1. 이전 상태 정리 (on_exit 호출)
        # 현재 상태 객체를 가져옴
        old_state = self.states.get(self.current_state_name)
        # 해당 객체에 on_exit 함수가 있다면 실행
        if old_state and hasattr(old_state, 'on_exit'):
            old_state.on_exit(self.context)

        print(f"🔄 State Transition: {self.current_state_name} -> {state_name}")
        self.current_state_name = state_name

        # 2. 새로운 상태 진입 설정 (on_enter 호출)
        new_state = self.states.get(state_name)
        if new_state:
            # 해당 객체에 on_enter 함수가 있다면 실행
            if hasattr(new_state, 'on_enter'):
                new_state.on_enter(self.context)
        
        # IDLE일 경우 하드웨어 정지 (혹은 IDLEState를 만들어 on_enter에 넣어도 됨)
        if state_name == "IDLE": 
            self.hw.stop()

    def update(self):
        if self.current_state_name == "IDLE": return
        
        current_state = self.states.get(self.current_state_name)
        if current_state:
            next_state = current_state.process(self.context)
            if next_state: self.set_state(next_state)