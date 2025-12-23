import time
import cv2
from .base_state import BaseState

class OCRState(BaseState):
    def __init__(self, hardware, ocr_detector, map1, map2):
        self.hw = hardware
        self.ocr_detector = ocr_detector
        self.map1 = map1
        self.map2 = map2

    def process(self, context):
        print("[State] OCR 작업 시작")
        
        # 1. 카메라 회전 (기존 코드: id 4, 5번 서보)
        self.hw.move_servo(4, 60, velocity=100)
        self.hw.move_servo(5, 45, velocity=100, delay=2.0)
        
        # 2. 이미지 촬영 및 보정
        frame = self.hw.get_frame()
        if frame is not None:
            # 어안 렌즈 보정
            frame = cv2.remap(frame, self.map1, self.map2, 
                              interpolation=cv2.INTER_LINEAR, 
                              borderMode=cv2.BORDER_CONSTANT)
            
            # 3. OCR 수행
            try:
                print("   -> 텍스트 분석 중...")
                # OCR Detector는 외부에서 주입받음
                result = self.ocr_detector.detect(frame, target='187고1604')
                
                if result and hasattr(result, 'text'):
                    context.ocr_result = result.text
                    print(f"   -> [성공] 인식된 텍스트: {result.text}")
                else:
                    context.ocr_result = "인식 실패"
            except Exception as e:
                print(f"   -> [에러] {e}")
        
        # 4. 카메라 원위치
        self.hw.move_servo(4, 0, velocity=100)
        self.hw.move_servo(5, 20, velocity=100, delay=1.0)
        
        # 5. 미션 플래그 설정 및 로봇팔 작업으로 전환
        return "ARM_IK"