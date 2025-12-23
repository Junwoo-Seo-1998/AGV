import time
from .context import RobotContext

# =========================================================
# [변경점] vision이 module 안에 있으므로 상대 경로(.)로 임포트
# =========================================================
try:
    from .vision.color import ColorRecognizer
    from .vision.detector import PlateNumberDetector
except ImportError as e:
    print(f"⚠️ Vision 모듈 임포트 실패: {e}")
    print("vision 폴더가 module 폴더 안에 있는지 확인해주세요.")
    ColorRecognizer = None
    PlateNumberDetector = None

class OCRCheckState:
    def __init__(self, hardware):
        self.hw = hardware
        # OCR 탐지기 초기화 (Clova 모델 사용)
        if PlateNumberDetector:
            # .env 파일은 노트북(AGV_TEST.ipynb)이 있는 경로에 있어야 합니다.
            self.detector = PlateNumberDetector(model="clova") 
        else:
            self.detector = None

    def process(self, context):
        print(f"[OCR State] 색상 지점 도착! 정지 후 번호판 탐색 시작 (타겟: {context.target_plate})")
        
        # 1. 로봇 정지
        self.hw.stop()
        time.sleep(0.5)

        # 2. 카메라 회전 (하드웨어 클래스에 추가된 rotate_camera 사용)
        print("[OCR State] 카메라 회전 중...")
        self.hw.rotate_camera(60, 4)
        self.hw.rotate_camera(45, 5)
        time.sleep(1.0) 

        # 3. 이미지 획득 및 OCR 수행
        frame = self.hw.get_frame()
        result_state = "TRACKING" # 기본적으로는 다시 주행으로 복귀
        
        if frame is not None and self.detector:
            # 타겟 번호판이 있는지 확인
            found_plate = self.detector.detect(frame, target=context.target_plate)
            
            if found_plate:
                print(f"🎉 [OCR State] 목표 차량 발견 성공! : {found_plate.text}")
                result_state = "IDLE" # 목표 찾음 -> 종료
            else:
                print("❌ [OCR State] 목표 차량 아님. 주행 재개.")
        
        # 4. 카메라 원위치 복귀
        print("[OCR State] 카메라 정면 복귀")
        self.hw.rotate_camera(0, 4)
        self.hw.rotate_camera(20, 5)
        time.sleep(0.5)

        return result_state


class LineTrackingState:
    def __init__(self, hardware, brain):
        self.hw = hardware
        self.brain = brain
        
        # 색상 인식기 초기화
        if ColorRecognizer:
            self.color_recognizer = ColorRecognizer()
        else:
            self.color_recognizer = None

    def process(self, context):
        image = self.hw.get_frame()
        if image is None: 
            return None 

        # [색상 감지 로직]
        if self.color_recognizer:
            color_res = self.color_recognizer.recognize(image)
            
            if color_res:
                # 새로운 색상일 때만 OCR 상태로 전환 (중복 방지)
                if context.last_detected_color != color_res.color:
                    print(f"🎨 [LineTracking] 색상 감지됨: {color_res.color} -> OCR 체크 실행")
                    context.last_detected_color = color_res.color 
                    return "OCR_CHECK"
            else:
                context.last_detected_color = None

        # [기본 주행]
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
        print(f"🔄 State Transition: {self.current_state_name} -> {state_name}")
        self.current_state_name = state_name
        if state_name == "IDLE":
            self.hw.stop()

    def update(self):
        if self.current_state_name == "IDLE":
            return

        current_state_obj = self.states.get(self.current_state_name)
        if current_state_obj:
            next_state = current_state_obj.process(self.context)
            if next_state:
                self.set_state(next_state)