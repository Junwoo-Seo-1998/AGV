from vision.color import ColorRecognizer
import cv2  # [추가] 이미지 리사이즈를 위해 OpenCV 사용

class LineTrackingState:
    def __init__(self, hardware, brain):
        self.hw = hardware
        self.brain = brain
        self.color_recognizer = ColorRecognizer()

    def process(self, context):
        # 1. 고해상도(816x616) 원본 이미지 가져오기
        image_full = self.hw.get_frame()
        if image_full is None: return None 

        # 2. [수정] 주행 및 색상 인식을 위해 224x224로 리사이즈
        # 리사이즈 연산은 매우 빠르므로 주행 루프에 부담을 주지 않습니다.
        image_resized = cv2.resize(image_full, (224, 224))

        # 3. 색상 감지 (리사이즈된 이미지 사용)
        color_res = self.color_recognizer.recognize(image_resized)
        if color_res and context.last_detected_color != color_res.color:
            print(f"🎨 색상 감지: {color_res.color}")
            context.last_detected_color = color_res.color 
            return "OCR_CHECK"
        elif not color_res:
            context.last_detected_color = None

        # 4. 주행 (리사이즈된 이미지 사용)
        # brain 모델은 224x224 입력을 기대하므로 리사이즈된 이미지를 넘겨줍니다.
        left, right = self.brain.calculate(image_resized, context)
        self.hw.drive(left, right)
        return None