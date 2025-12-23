import time
from .context import RobotContext

# 이제 vision이 바로 옆에 있으므로 아주 깔끔하게 import 됩니다.
from vision.color import ColorRecognizer
from vision.detector import PlateNumberDetector
import cv2
import numpy as np

# 1. [신규] 짐 찾기 및 접근 상태 (Visual Servoing)
class LoadSearchState:
    def __init__(self, hardware):
        self.hw = hardware
        self.min_cnt_size = 50
        
        # [추가] 바닥 인식을 위한 흰색 범위 (vision/color.py 참조)
        # 현장 조명에 따라 튜닝이 필요할 수 있습니다.
        self.floor_range = {
            'lower': np.array([0, 0, 163]), 
            'upper': np.array([179, 50, 255])
        }

    def process(self, context):
        frame = self.hw.get_frame()
        if frame is None: return None
        
        h, w = frame.shape[:2]
        
        # 1. 이미지 전처리 (HSV 변환)
        # vision/color.py 처럼 밝기 보정(CLAHE)을 넣으면 더 좋습니다.
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 2. [핵심] 바닥 마스크 생성 (Floor Mask)
        # 흰색 바닥만 추출합니다.
        floor_mask = cv2.inRange(hsv, self.floor_range['lower'], self.floor_range['upper'])
        
        # 바닥의 구멍(타일 줄눈 등)을 메우는 연산 (Morphology Close)
        kernel = np.ones((5,5), np.uint8)
        floor_mask = cv2.morphologyEx(floor_mask, cv2.MORPH_CLOSE, kernel)
        
        # 화면 상단(배경)은 강제로 지워버립니다. (천장 조명 등 노이즈 제거)
        exclude_top = int(h * 0.25)
        floor_mask[:exclude_top, :] = 0
        
        # 3. 짐 색상 마스크 생성 (Object Mask)
        object_mask = cv2.inRange(hsv, np.array(context.load_color_range['lower']), 
                                       np.array(context.load_color_range['upper']))
        
        # 4. [핵심] 바닥 위에 있는 물체만 남기기 (AND 연산)
        # "바닥이면서" 동시에 "짐 색상"인 것만 추출
        final_mask = cv2.bitwise_and(floor_mask, object_mask)
        
        # 노이즈 제거 (Erode/Dilate)
        final_mask = cv2.erode(final_mask, None, iterations=1)
        final_mask = cv2.dilate(final_mask, None, iterations=1)
        
        # 5. 컨투어 찾기 (이후 로직은 동일)
        cnts, _ = cv2.findContours(final_mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        center_x = -1
        if len(cnts) > 0:
            c = max(cnts, key=cv2.contourArea)
            if cv2.contourArea(c) > self.min_cnt_size:
                x, y, w, h = cv2.boundingRect(c)
                center_x = int(x + (w / 2))
                # center_y = int(y + (h / 2)) # 필요시 사용

        # --- 제어 로직 (기존과 동일) ---
        if center_x < 0:
            print("🔍 짐 찾는 중... (바닥 위 탐색)")
            self.hw.drive(0.15, -0.15) # 제자리 회전
            return None

        err_margin = context.align_error_margin
        target_x = context.grab_zone_x
        
        if center_x < target_x - err_margin:
            self.hw.drive(-0.1, 0.1)
        elif center_x > target_x + err_margin:
            self.hw.drive(0.1, -0.1)
        else:
            print("🎯 짐 정렬 완료! 잡기 시도")
            self.hw.stop()
            time.sleep(0.5)
            return "GRAB"

        return None
    
# 2. [신규] 짐 잡기 상태
class GrabState:
    def __init__(self, hardware):
        self.hw = hardware

    def process(self, context):
        print("⚡ [State] 짐 잡기 수행...")
        success = self.hw.arm_grab()
        
        if success:
            context.is_holding = True
            print("✅ 잡기 성공! 로드 팔로잉(TRACKING) 시작")
            return "TRACKING"
        else:
            return "IDLE" # 실패 시 정지
        
# 3. [신규] 짐 놓기 상태
class ReleaseState:
    def __init__(self, hardware):
        self.hw = hardware

    def process(self, context):
        print("⚡ [State] 목표 지점 도착. 짐 놓기 수행...")
        self.hw.arm_release()
        
        context.is_holding = False
        print("✅ 배달 완료! 집으로 복귀합니다.")
        return "TRACKING" # 다시 주행하여 집으로 복귀


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
        self.hw.rotate_camera(60, 1)
        self.hw.rotate_camera(45, 5)
        time.sleep(1.0) 

        # 이미지 획득 및 OCR
        frame = self.hw.get_frame()
        result_state = "TRACKING"
        
        if frame is not None:
            found_plate = self.detector.detect(frame, target=context.target_plate)
            # [핵심 로직 변경] OCR 결과가 타겟과 일치하면 -> 짐을 놓는다
            if found_plate and found_plate.text == context.target_plate:
                print(f"🎉 타겟 일치 ({found_plate.text}) -> 배달(Release)")
                next_state = "RELEASE"
            else:
                print("❌ 타겟 아님. 계속 주행.")


        # 카메라 복귀
        self.hw.rotate_camera(0, 1)
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
            detected_color = color_res.color
            context.last_detected_color = detected_color
            print(f"🎨 색상 감지: {detected_color}")

            # [분기 로직]
            if context.is_holding:
                # 짐을 들고 있을 때 색상 발견 -> 정지 후 OCR 체크
                print("🛑 체크포인트 발견 -> OCR 확인")
                return "OCR_CHECK"
            
            else:
                # 짐을 내려놓고 복귀 중일 때 -> 집 색상이면 정지
                if detected_color == context.home_color:
                    print(f"🏠 집({context.home_color}) 도착! 미션 종료.")
                    return "IDLE"
                else:
                    print("🚗 집이 아니므로 통과")

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
        self.brain = brain      
        self.states = {
            "LOAD_SEARCH": LoadSearchState(hardware), # 1. 짐 찾기
            "GRAB": GrabState(hardware),              # 2. 잡기
            "TRACKING": LineTrackingState(hardware, brain), # 3. 주행 (로드팔로잉 + 복귀)
            "OCR_CHECK": OCRCheckState(hardware),     # 4. 정지 후 OCR
            "RELEASE": ReleaseState(hardware),        # 5. 짐 놓기
            "IDLE": None
        }
        # 시작 상태를 'LOAD_SEARCH'로 설정 (짐 찾기부터 시작)
        self.current_state_name = "LOAD_SEARCH"

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