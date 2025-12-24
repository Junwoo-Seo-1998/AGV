from vision.color import ColorRecognizer

class LineTrackingState:
    def __init__(self, hardware, brain):
        self.hw = hardware
        self.brain = brain
        self.color_recognizer = ColorRecognizer() # 바로 사용 가능
        
    def on_enter(self, context):
        print("🚀 라인 트래킹 시작 (Camera: 224x224)")
        self.hw.set_camera_resolution(224, 224)
        
    def process(self, context):
        # [수정] 라인 트래킹은 224x224 해상도 사용 (변경 필요 시에만 내부적으로 재시작됨)
        #self.hw.set_camera_resolution(224, 224)

        image = self.hw.get_frame()
        if image is None: return None 

        # 색상 감지
        color_res = self.color_recognizer.recognize(image)
        if color_res:
            # (A) 새로운 색상이면 -> '방문함' 체크하고 접근 모드로 전환
            if context.last_detected_color != color_res.color:
                print(f"🎨 새로운 타겟 발견: {color_res.color} -> 정밀 접근 시작")
                
                # [핵심] 여기서 미리 업데이트 (중복 방지)
                context.last_detected_color = color_res.color 
                
                return "APPROACH"
            
            # (B) 이미 처리한 색상(OCR 하고 돌아온 상태)이면 -> Pass (주행 로직으로 넘어감)
            else:
                pass 
                
        else:
            # (C) 색상이 시야에서 완전히 사라지면 -> 초기화
            context.last_detected_color = None

        # 주행
        left, right = self.brain.calculate(image, context)
        self.hw.drive(left, right)
        return None