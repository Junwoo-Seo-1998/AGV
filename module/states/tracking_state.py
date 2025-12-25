from vision.color import ColorRecognizer
from SCSCtrl import TTLServo
import time

class LineTrackingState:
    def __init__(self, hardware, brain):
        self.hw = hardware
        self.brain = brain
        self.color_recognizer = ColorRecognizer()

    def on_enter(self, context):
        print("🚀 라인 트래킹 시작 (Camera: 224x224)")

        
        self.hw.set_camera_resolution(224, 224)

    def process(self, context):
        image = self.hw.get_frame()
        if image is None: return None 

        color_res = self.color_recognizer.recognize(image)
        
        if color_res:
            # (A) 완전히 새로운 색상인 경우에만 접근 모드 시작
            
            if context.last_detected_color != color_res.color:
                
                if color_res.color == "orange":
                    context.last_detected_color = color_res.color
                    print("orange 발견! 집기 시작!")
                    return "FIND_TARGET"
                
                print(f"🎨 새로운 타겟 발견: {color_res.color} -> 정밀 접근 시작")
                context.last_detected_color = color_res.color # 업데이트
                return "APPROACH"
            
            # (B) 방금 처리한 색상(OCR 완료한 색)이면 -> 무시하고 그냥 지나감
            else:
                pass 
        
        # [핵심 수정] 
        # else: context.last_detected_color = None  <-- 이 줄을 삭제했습니다!
        # 이유: 잠깐 색을 놓쳤다고 변수를 지워버리면, 다시 보였을 때 '새로운 색'인 줄 알고 또 멈춥니다.
        # 그냥 놔두면, 로봇이 전진해서 나중에 '다른 색'을 만나거나 프로그램이 재시작될 때 갱신됩니다.

        # 주행
        left, right = self.brain.calculate(image, context)
        self.hw.drive(left, right)
        
        return None