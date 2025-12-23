class RobotContext:
    def __init__(self):
        # RobotMoving.py에서 슬라이더로 조절하던 값들
        self.speed_gain = 0.25      
        self.steering_gain = 0.1   
        self.steering_dgain = 0.25   
        self.steering_bias = 0.0    
        
        # 주행 상태 모니터링용 변수
        self.current_x = 0.0
        self.current_y = 0.0
        self.processed_image = None 
        
        # [추가] OCR 및 미션 관련 변수
        self.target_plate = "123가4568"  # 찾고자 하는 목표 번호판
        self.last_detected_color = None  # 같은 색상 지점에서 반복 정지를 막기 위한 변수

        # [추가] 짐(Load) 및 복귀 관련 상태 변수
        self.is_holding = False          # 현재 짐을 잡고 있는지 여부
        self.home_color = "orange"       # 복귀할 집의 색상 (예: 오렌지색)
        
        # [추가] 짐 찾기(Visual Servoing) 설정
        self.load_color_range = {        # 짐의 색상 (toy_clearner의 red 예시)
            'lower': (160, 100, 100), 
            'upper': (180, 255, 255)
        }
        self.grab_zone_x = 112           # 짐을 잡기 위한 화면상 X 중심 좌표 (카메라 해상도에 맞춰 조정 필요)
        self.grab_zone_y = 224           # 짐이 도달해야 할 Y 좌표 (가까움 정도)
        self.align_error_margin = 20     # 정렬 허용 오차

        # 짐찾기 / 잡기 -> 주행 -> 색상 인식 -> OCR -> 조건 일치시 (짐 놓기) -> 집으로 복귀

        