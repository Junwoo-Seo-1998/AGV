import cv2
import numpy as np
import time
from SCSCtrl import TTLServo

class FindTargetState:
    def __init__(self, hardware):
        self.hw = hardware
        
        # --- [원본 글로벌 변수 및 설정값] ---
        self.screen_w = 300
        self.screen_h = 300
        
        # 색상 범위 (원본 값 유지)
        self.lower_red = np.array([160, 100, 100])
        self.upper_red = np.array([180, 255, 255])
        self.lower_yellow = np.array([0, 50, 0])
        self.upper_yellow = np.array([30, 255, 255])
        self.lower_blue = np.array([90, 100, 100])
        self.upper_blue = np.array([120, 255, 200])

        self.min_cnt_size = 50
        
        self.grab_zone_x = 140
        self.grab_zone_y = 240
        self.error_margin = 10
        
        self.speed = 0.3

    def find_toy_pos(self, input_image):
        # [원본 함수: find_toy_pos]
        
        # Convert video frames to HSV color space.
        hsv = cv2.cvtColor(input_image, cv2.COLOR_BGR2HSV)
        
        # Create masks
        mask_red = cv2.inRange(hsv, self.lower_red, self.upper_red)
        mask_yellow = cv2.inRange(hsv, self.lower_yellow, self.upper_yellow)
        mask_blue = cv2.inRange(hsv, self.lower_blue, self.upper_blue)
        
        # Combining the masks & Denoising
#         result = mask_red + mask_yellow + mask_blue
        result = mask_blue
        result = cv2.erode(result, None, iterations=1)
        result = cv2.dilate(result, None, iterations=1)
        
        # Find contours
        cnts = cv2.findContours(result.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
        
        if len(cnts) > 0:
            c = max(cnts, key=cv2.contourArea)
            
            if cv2.contourArea(c) > self.min_cnt_size:
                x, y, w, h = cv2.boundingRect(c)
                center_x = int(x + (w / 2))
                center_y = int(y + (h / 2))
                
                # [원본 시각화 유지]
                cv2.circle(input_image, (center_x, center_y), 2, (255, 255, 255), -1)
                cv2.rectangle(input_image, (x, y), (x + w, y + h), (255, 255, 255), 1)
                
                return center_x, center_y
            else:
                return -1, -1
        else:
            return -1, -1

    def drive_to_position(self, input_image, zone_x, zone_y, center_x, center_y):
        # [원본 구조 복구] return False 제거 -> 아래쪽 코드가 이어서 실행됨
        
        # --- 1. Left/Right Control ---
        if center_x < 0:
            self.hw.stop()
            cv2.circle(input_image, (zone_x, zone_y), self.error_margin, (0, 0, 0), 1)
            
        elif center_x < zone_x - self.error_margin:
            # Left
            print(f"⬅️ Left (cx:{center_x})")
            self.hw.drive(-self.speed, self.speed)
            cv2.putText(input_image, 'Left', (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.circle(input_image, (zone_x, zone_y), self.error_margin, (0, 0, 0), 1)
            # return False 없음 -> 바로 아래 코드로 진입
            
        elif center_x > zone_x + self.error_margin:
            # Right
            print(f"➡️ Right (cx:{center_x})")
            self.hw.drive(self.speed, -self.speed)
            cv2.putText(input_image, 'Right', (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.circle(input_image, (zone_x, zone_y), self.error_margin, (0, 0, 0), 1)
            # return False 없음 -> 바로 아래 코드로 진입

        # --- 2. Forward/Backward Control ---
        # 원본 로직: 여기서 명령을 내리면 위에서 내린 회전 명령이 덮어씌워짐 (전진 우선)
        
        if center_y < 0:
            self.hw.stop()
            cv2.circle(input_image, (zone_x, zone_y), self.error_margin, (0, 0, 0), 1)
            
        elif center_y < zone_y - self.error_margin:
            # Forward
            print(f"⬆️ Forward (cy:{center_y})")
            self.hw.drive(self.speed, self.speed)
            cv2.putText(input_image, 'Forward', (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.circle(input_image, (zone_x, zone_y), self.error_margin, (0, 0, 0), 1)
            
        elif center_y > zone_y + self.error_margin:
            # Backward
            print(f"⬇️ Backward (cy:{center_y})")
            self.hw.drive(-self.speed, -self.speed)
            cv2.putText(input_image, 'Backwards', (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.circle(input_image, (zone_x, zone_y), self.error_margin, (0, 0, 0), 1)

        # --- 3. 정렬 완료 체크 ---
        if (center_x > zone_x - self.error_margin and center_x < zone_x + self.error_margin and 
            center_y > zone_y - self.error_margin and center_y < zone_y + self.error_margin):
            
            print("🎯 정렬 완료 (Target Locked)")
            self.hw.stop()
            cv2.circle(input_image, (zone_x, zone_y), self.error_margin, (255, 255, 255), 1)
            return True

        return False
    
    
    def on_enter(self, context):
        print(f"📸 물체집기 시작.")
        TTLServo.servoAngleCtrl(1, 0, 1, 150)
        TTLServo.servoAngleCtrl(2, 0, 1, 150)
        TTLServo.servoAngleCtrl(3, 0, 1, 150)
        TTLServo.servoAngleCtrl(4, 100, 1, 150)
        TTLServo.servoAngleCtrl(5, 40, 1, 150)
        
        time.sleep(1)
        self.hw.set_camera_resolution(self.screen_w, self.screen_h)

    def process(self, context):
        # [원본 함수: execute 역할]
        
        
        # 1. 해상도 설정 (300x300)
        self.hw.set_camera_resolution(self.screen_w, self.screen_h)
        image = self.hw.get_frame()
        if image is None: return None

        # 2. 물체 찾기
        center_x, center_y = self.find_toy_pos(image)
        
        # 3. 이동 로직
        in_position = self.drive_to_position(image, self.grab_zone_x, self.grab_zone_y, center_x, center_y)
        
        # 4. 집기 (Blocking 방식)
        if in_position:
            print("✅ In Position! Starting Grab.")
            self.hw.grab_object() # hardware.py에 정의된 함수 호출
            return "TRACKING" # 집기 완료 후 상태 변경

        return None