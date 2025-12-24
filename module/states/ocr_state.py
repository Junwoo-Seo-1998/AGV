import time
# vision 패키지는 프로젝트 루트에 있으므로 절대 경로 import 사용
from vision.detector import PlateNumberDetector

class OCRCheckState:
    def __init__(self, hardware):
        self.hw = hardware
        # OCR 탐지기 초기화
        self.detector = PlateNumberDetector(model="clova") 

    def process(self, context):
        print(f"[OCR State] 번호판 탐색 시작 (타겟: {context.target_plate})")
        
        self.hw.stop()
        time.sleep(0.5)

        # 카메라 회전
        self.hw.rotate_camera(60, 4)
        self.hw.rotate_camera(45, 5)
        time.sleep(1.0) 

        # 이미지 획득 및 OCR
        frame = self.hw.get_frame()
        result_state = "TRACKING"
        
        if frame is not None:
            found_plate = self.detector.detect(frame, target=context.target_plate)
            if found_plate:
                print(f"🎉 목표 발견 성공: {found_plate.text}")
                result_state = "IDLE"
            else:
                print("❌ 목표 아님. 주행 재개.")
        
        # 카메라 복귀
        self.hw.rotate_camera(0, 4)
        self.hw.rotate_camera(20, 5)
        time.sleep(0.5)

        return result_state