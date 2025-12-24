import cv2
import numpy as np

class ToyDetector:
    def __init__(self):
        # 색상 범위 설정 (Red, Yellow, Blue)
        self.lower_red = np.array([160, 100, 100])
        self.upper_red = np.array([180, 255, 255])
        
        self.lower_yellow = np.array([0, 50, 0])
        self.upper_yellow = np.array([30, 255, 255])
        
        self.lower_blue = np.array([90, 100, 100])
        self.upper_blue = np.array([120, 255, 200])
        
        self.min_cnt_size = 50

    def find_pos(self, input_image):
        # HSV 변환
        hsv = cv2.cvtColor(input_image, cv2.COLOR_BGR2HSV)
        
        # 마스크 생성
        mask_red = cv2.inRange(hsv, self.lower_red, self.upper_red)
        mask_yellow = cv2.inRange(hsv, self.lower_yellow, self.upper_yellow)
        mask_blue = cv2.inRange(hsv, self.lower_blue, self.upper_blue)
        
        # 마스크 합치기
        result = mask_red + mask_yellow + mask_blue
        
        # 노이즈 제거 (Erode & Dilate)
        result = cv2.erode(result, None, iterations=1)
        result = cv2.dilate(result, None, iterations=1)
        
        # 컨투어 찾기
        cnts = cv2.findContours(result.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
        
        if len(cnts) > 0:
            # 가장 큰 영역 찾기
            c = max(cnts, key=cv2.contourArea)
            
            if cv2.contourArea(c) > self.min_cnt_size:
                x, y, w, h = cv2.boundingRect(c)
                center_x = int(x + (w / 2))
                center_y = int(y + (h / 2))
                
                # 디버깅용 그림 그리기 (옵션)
                cv2.circle(input_image, (center_x, center_y), 5, (0, 255, 0), -1)
                
                return center_x, center_y
        
        return -1, -1