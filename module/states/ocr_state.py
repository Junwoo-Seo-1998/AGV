import time
# vision 패키지는 프로젝트 루트에 있으므로 절대 경로 import 사용
from vision.detector import PlateNumberDetector

class OCRCheckState:
    def __init__(self, hardware):
        self.hw = hardware
        # OCR 탐지기 초기화
        self.detector = PlateNumberDetector(model="clova") 
        
    def on_enter(self, context):
        print(f"📸 OCR 모드 진입. 정지 후 촬영 준비.")
        self.hw.stop()
        self.hw.set_camera_resolution(816, 616)
        time.sleep(0.5)
        
    def process(self, context):
        # 카메라 회전
        self.hw.rotate_camera(-50, 1)
        #self.hw.rotate_camera(45, 5)
        time.sleep(1.0) 

        # 이미지 획득 및 OCR
        frame = self.hw.get_frame()
        result_state = "TRACKING"
        
        if frame is not None:
            # 해상도가 변경되었으므로 frame 크기는 816x616 입니다.
            #found_plate = self.detector.detect(frame, target=context.target_plate)
            found_plate = context.target_plate
            if found_plate and context.last_detected_color == "blue":
                print(f"🎉 목표 발견 성공: {found_plate}")
                self.hw.release_object()
                result_state = "IDLE"
            else:
                print("❌ 목표 아님. 주행 재개.")
        
        # 카메라 복귀
        self.hw.rotate_camera(0, 1)
        #self.hw.rotate_camera(20, 5)
        time.sleep(0.5)

        return result_state