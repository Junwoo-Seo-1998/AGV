import cv2
import numpy as np
from vision.result import ColorRecognitionResult
from vision.utils.image_proc import apply_white_balance, apply_clahe_color


class ColorRecognizer:

    def __init__(
            self,
            min_detection_area_ratio=0.09,  # 탐지로 판정할 전체 대비 최소 면적 비율 기준
            exclude_top_ratio=0.25,  # 상단 노이즈 제거 비율 (0 ~ n)
            include_bottom_ratio=0.5,  # 하단 강제 포함 비율 (n ~ 1.0)
            white_balancing_p =0.5,   # 화이트 밸런싱 적용 강도
            apply_enhance_brightness = True,    # 밝기 조정 전처리 적용 여부
    ):
        # 색상 탐지 기준 초기화
        self.min_detection_area_ratio = min_detection_area_ratio

        # ROI 영역 관련 수치 초기화
        self.exclude_top_ratio = exclude_top_ratio
        self.include_bottom_ratio = include_bottom_ratio

        # 이미지 전처리 관련
        self.white_balancing_p = white_balancing_p
        self.apply_enhance_brightness = apply_enhance_brightness

        # 색상 hsv 범위
        self.white_range = (np.array([0, 0, 163]), np.array([179, 50, 255]))
        self.color_ranges = {
            'red': [(0, 70, 115), (7, 255, 255), (167, 80, 83), (179, 255, 255)],
            'orange': [(9, 70, 87), (19, 255, 255)],
            'yellow': [(21, 68, 121), (34, 255, 255)],
            'green': [(43, 83, 114), (88, 255, 255)],
            'blue': [(100, 70, 116), (116, 255, 255)],
            'purple': [(120, 61, 82), (151, 255, 255)]
        }

    def _get_floor_mask(self, hsv, h):
        # 흰색 바닥 추출
        floor_mask = cv2.inRange(hsv, self.white_range[0], self.white_range[1])

        # 상단 영역은 강제로 제외 (배경 노이즈 제거)
        top_limit = int(h * self.exclude_top_ratio)
        bottom_limit = int(h * self.include_bottom_ratio)  # 하단 일부는 무조건 유지
        floor_mask[:top_limit, :] = 0
        floor_mask[bottom_limit:, :] = 255

        # 바닥 마스크 내부의 구멍(타일)을 채우기
        # 1. 마스크에서 윤곽선 찾기
        contours, _ = cv2.findContours(floor_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        filled_mask = np.zeros_like(floor_mask)
        if contours:
            # 2. 그중 가장 면적이 넓은 컨투어(바닥일 확률 높음) 선택
            largest_contour = max(contours, key=cv2.contourArea)

            # 3. 해당 컨투어 안쪽을 흰색(255)으로 꽉 채움 (두께 -1이 채우기 옵션)
            cv2.drawContours(filled_mask, [largest_contour], -1, 255, thickness=cv2.FILLED)

        return filled_mask

    def _get_color_masks(self, hsv):
        masks = {}
        for color_name, boundaries in self.color_ranges.items():
            if color_name == 'red': # 빨간색은 두 범위를 합침
                mask1 = cv2.inRange(hsv, boundaries[0], boundaries[1])
                mask2 = cv2.inRange(hsv, boundaries[2], boundaries[3])
                masks[color_name] = cv2.bitwise_or(mask1, mask2)
            else:
                masks[color_name] = cv2.inRange(hsv, boundaries[0], boundaries[1])
        return masks

    def recognize(
            self,
            frame,
            min_detection_area_ratio = None,
            return_mask = False  # 반환 시 인식한 색 영역의 마스크도 반환할지
    ):
        if min_detection_area_ratio is None:
            min_detection_area_ratio = self.min_detection_area_ratio

        img = frame.copy()
        h, w = img.shape[:2]

        # 밝기 조정 옵션
        if self.apply_enhance_brightness:
            img = apply_clahe_color(img)

        # 톤 밸런싱 적용
        img = apply_white_balance(img, self.white_balancing_p)

        # HSV 값 구하기
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # 바닥 ROI 마스크 생성
        floor_roi_mask = self._get_floor_mask(hsv, h)

        # 색상별 마스크 생성
        color_masks = self._get_color_masks(hsv)

        # 색상 영역을 추출하여 가장 큰 색상 영역 찾기
        largest_area_size = 0
        largest_color = None
        largest_color_mask = None
        for color_name, color_mask in color_masks.items():
            roi_color_mask = cv2.bitwise_and(floor_roi_mask, color_mask)
            area_size = cv2.countNonZero(roi_color_mask)
            area_size_ratio = area_size / (h * w)

            if area_size_ratio > largest_area_size:
                largest_area_size = area_size_ratio
                largest_color = color_name
                largest_color_mask = roi_color_mask

        if largest_area_size >= min_detection_area_ratio:
            
            M = cv2.moments(largest_color_mask)
            cy = 0
            if M["m00"] > 0:
                cy = int(M["m01"] / M["m00"]) # 중심 Y좌표
            
            return ColorRecognitionResult(
                color=largest_color,
                area_ratio=largest_area_size,
                center_y=cy,
                mask=largest_color_mask if return_mask else None
            )
        else:
            return None

