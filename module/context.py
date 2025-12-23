# modules/context.py

class RobotContext:
    def __init__(self):
        # [기존] 주행 설정 값
        self.speed_gain = 0.15
        self.steering_gain = 0.04
        self.steering_dgain = 0.0
        self.steering_bias = 0.0
        
        # [기존] 모니터링 변수
        self.current_x = 0.0
        self.current_y = 0.0
        self.processed_image = None
        
        # [신규] 미션 관련 공유 데이터
        self.detected_color = None  # 예: 'RED', 'BLUE'
        self.ocr_result = None      # OCR 인식된 텍스트
        self.is_mission_completed = False # 미션 완료 플래그