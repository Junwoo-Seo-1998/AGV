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