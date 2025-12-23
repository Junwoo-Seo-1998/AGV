from .context import RobotContext

# 상태 클래스: 라인 트레킹 (기본 주행)
class LineTrackingState:
    def __init__(self, hardware, brain):
        self.hw = hardware
        self.brain = brain

    def process(self, context):
        image = self.hw.get_frame()
        if image is None: 
            return None # 카메라 없으면 대기

        # 1. Brain을 통해 모터 값 계산
        left, right = self.brain.calculate(image, context)
        
        # 2. 하드웨어 제어
        self.hw.drive(left, right)
        
        # 3. 상태 전이 로직 (지금은 무조건 주행만 하므로 None 반환)
        # 예: if check_obstacle(): return "OBSTACLE_AVOID"
        return None 


class MissionManager:
    def __init__(self, hardware, brain):
        self.context = RobotContext() # 설정값 저장소
        self.hw = hardware
        
        # 사용할 상태들 등록
        self.states = {
            "TRACKING": LineTrackingState(hardware, brain),
            "IDLE": None
        }
        self.current_state_name = "IDLE" 

    def set_state(self, state_name):
        print(f"Set State: {state_name}")
        self.current_state_name = state_name
        if state_name == "IDLE":
            self.hw.stop()

    def update(self):
        """메인 루프에서 계속 호출될 함수"""
        if self.current_state_name == "IDLE":
            return

        current_state_obj = self.states.get(self.current_state_name)
        if current_state_obj:
            # 현재 상태 실행 후 다음 상태 확인
            next_state = current_state_obj.process(self.context)
            
            if next_state:
                self.set_state(next_state)