import time
from vision.detector import PlateNumberDetector

class OCRCheckState:
    def __init__(self, hardware):
        self.hw = hardware
        self.detector = PlateNumberDetector(model="clova") 

    def process(self, context):
        print(f"[OCR State] 번호판 탐색 시작 (타겟: {context.target_plate})")
        
        self.hw.stop()
        time.sleep(0.5) # 정지 후 안정화 대기

        # 카메라 회전
        self.hw.rotate_camera(-60, 1)
        self.hw.rotate_camera(45, 5)
        time.sleep(1.0) 

        # 이미지 획득 및 OCR
        # [수정] 별도 해상도 변경 없이 바로 가져오면 816x616 고해상도 이미지입니다.
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
        self.hw.rotate_camera(0, 1)
        self.hw.rotate_camera(20, 5)
        time.sleep(0.5)

        return result_state