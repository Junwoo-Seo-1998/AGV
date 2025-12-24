from vision.color import ColorRecognizer

class LineTrackingState:
    def __init__(self, hardware, brain):
        self.hw = hardware
        self.brain = brain
        self.color_recognizer = ColorRecognizer() # 바로 사용 가능

    def process(self, context):
        # [수정] 라인 트래킹은 224x224 해상도 사용 (변경 필요 시에만 내부적으로 재시작됨)
        self.hw.set_camera_resolution(224, 224)

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