import time
from .context import RobotContext

# 이제 vision이 바로 옆에 있으므로 아주 깔끔하게 import 됩니다.
from vision.color import ColorRecognizer
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


class LineTrackingState:
    def __init__(self, hardware, brain):
        self.hw = hardware
        self.brain = brain
        self.color_recognizer = ColorRecognizer() # 바로 사용 가능

    def process(self, context):
        image = self.hw.get_frame()
        if image is None: return None 

        # 색상 감지
        color_res = self.color_recognizer.recognize(image)
        if color_res and context.last_detected_color != color_res.color:
            print(f"🎨 색상 감지: {color_res.color}")
            context.last_detected_color = color_res.color 
            return "OCR_CHECK"
        elif not color_res:
            context.last_detected_color = None

        # 주행
        left, right = self.brain.calculate(image, context)
        self.hw.drive(left, right)
        return None 


class MissionManager:
    def __init__(self, hardware, brain):
        self.context = RobotContext()
        self.hw = hardware
        
        self.states = {
            "TRACKING": LineTrackingState(hardware, brain),
            "OCR_CHECK": OCRCheckState(hardware),
            "IDLE": None
        }
        self.current_state_name = "IDLE" 

    def set_state(self, state_name):
        print(f"🔄 State: {state_name}")
        self.current_state_name = state_name
        if state_name == "IDLE": self.hw.stop()

    def update(self):
        if self.current_state_name == "IDLE": return
        
        current_state = self.states.get(self.current_state_name)
        if current_state:
            next_state = current_state.process(self.context)
            if next_state: self.set_state(next_state)