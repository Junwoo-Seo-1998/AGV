class RobotContext:
    def __init__(self):
        # RobotMoving.py에서 슬라이더로 조절하던 값들
        self.speed_gain = 0.15      # speed_gain_slider
        self.steering_gain = 0.04   # steering_gain_slider
        self.steering_dgain = 0.0   # steering_dgain_slider
        self.steering_bias = 0.0    # steering_bias_slider
        
        # 주행 상태 모니터링용 변수
        self.current_x = 0.0
        self.current_y = 0.0
        self.processed_image = None # 디버깅용 JPEG 이미지 데이터