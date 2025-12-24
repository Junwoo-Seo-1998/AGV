import time
from vision.toy_detector import ToyDetector

class PickupState:
    def __init__(self, hardware):
        self.hw = hardware
        self.detector = ToyDetector()
        
        # [설정] 224x224 해상도 기준 목표 지점 설정
        # (원본 코드는 300x300에서 140, 240이었음 -> 비율 맞춰 조정)
        self.GRAB_ZONE_X = 112  # 화면 중앙 (Width / 2)
        self.GRAB_ZONE_Y = 190  # 화면 하단 (물체가 팔에 닿을 거리)
        self.ERROR_MARGIN = 15  # 허용 오차
        
        self.SPEED = 0.15       # 미세 조정 속도

    def on_enter(self, context):
        print("🧐 [PICKUP] 물체 정밀 탐색 및 접근 시작...")
        self.hw.set_camera_resolution(224, 224)

    def process(self, context):
        image = self.hw.get_frame()
        if image is None: return None

        # 1. 물체 위치 찾기
        cx, cy = self.detector.find_pos(image)
        
        # 2. 위치 제어 (drive_to_position 로직 이식)
        if cx < 0 or cy < 0:
            # 물체를 못 찾음 -> 정지
            self.hw.stop()
            print("❌ 물체 못 찾음 (시야 밖)")
            return None # 계속 탐색

        # X축 보정 (좌우 회전)
        if cx < self.GRAB_ZONE_X - self.ERROR_MARGIN:
            # Left
            print(f"⬅️ 좌회전 (cx:{cx})")
            self.hw.drive(-self.SPEED, self.SPEED)
            
        elif cx > self.GRAB_ZONE_X + self.ERROR_MARGIN:
            # Right
            print(f"➡️ 우회전 (cx:{cx})")
            self.hw.drive(self.SPEED, -self.SPEED)
            
        # Y축 보정 (전후 이동)
        elif cy < self.GRAB_ZONE_Y - self.ERROR_MARGIN:
            # Forward (물체가 아직 멀다)
            print(f"⬆️ 전진 (cy:{cy})")
            self.hw.drive(self.SPEED, self.SPEED)
            
        elif cy > self.GRAB_ZONE_Y + self.ERROR_MARGIN:
            # Backward (너무 가까움)
            print(f"⬇️ 후진 (cy:{cy})")
            self.hw.drive(-self.SPEED, -self.SPEED)
            
        else:
            # [성공] 위치 정렬 완료!
            print("✅ 정위치 도달! 잡기 시도!")
            self.hw.stop()
            time.sleep(0.5) # 안정화
            
            # 3. 잡기 실행
            self.hw.grab_sequence()
            
            # 4. 완료 후 주행 복귀
            return "TRACKING"

        return None