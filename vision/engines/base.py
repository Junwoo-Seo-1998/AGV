from abc import ABC, abstractmethod
from vision.result import RawOCR, PlateResult
from typing import List
import numpy as np

class OCRBase(ABC):

    def __init__(
            self,
            *,
            y_center_ratio=0.2,
            min_height_ratio=0.6,
            max_spacing_ratio=0.1,
            debug_mode=False
    ):
        self.debug_mode = debug_mode
        self.y_center_ratio = y_center_ratio
        self.min_height_ratio = min_height_ratio
        self.max_spacing_ratio = max_spacing_ratio

    @abstractmethod
    def _recognize_raw(self, image: np.ndarray):
        """
        엔진별 raw OCR 결과 반환하는 raw 메소드
        예: [(text, score, bbox), ...]
        """
        pass

    def _merge_ocr_boxes(
            self,
            results: List[RawOCR],
            *,
            y_center_ratio: float,
            min_height_ratio: float,
            max_spacing_ratio: float
    ) -> List[RawOCR]:
        """
        인식 결과 중 병합해야 하는 문자열을 병합
        예를 들어 '640오8800'처럼 붙어있는 문자열인데 '640오'와 '8800'으로 분리되어 인식된 경우
        """
        if not results:
            return []

        # x1 기준 정렬
        results = sorted(results, key=lambda r: r.bbox[0])
        merged: List[RawOCR] = [results[0]]

        for result in results[1:]:
            text, score, bbox = result.text, result.confidence, result.bbox
            prev_text, prev_score, prev_bbox = merged[-1].text, merged[-1].confidence, merged[-1].bbox

            px1, py1, px2, py2 = prev_bbox
            x1, y1, x2, y2 = bbox
            prev_h = py2 - py1
            curr_h = y2 - y1
            prev_w = px2 - px1
            curr_w = x2 - x1

            # 1. -y축 정렬
            # center 기준 y축 중심이 비슷한 라인에 있는지
            prev_center_y = (py1 + py2) / 2
            curr_center_y = (y1 + y2) / 2
            y_center_diff = abs(prev_center_y - curr_center_y)
            y_align_ok = y_center_diff <= min(prev_h, curr_h) * y_center_ratio

            # 2. 높이 비율
            height_ratio = min(prev_h, curr_h) / max(prev_h, curr_h)
            height_ok = height_ratio >= min_height_ratio

            # 3. 문자 간 평균 폭 대비 거리
            avg_char_width = (prev_w + curr_w) / 2
            x_gap = x1 - px2
            spacing_ok = x_gap <= avg_char_width * max_spacing_ratio

            # 4. 병합 여부 판단
            if y_align_ok and height_ok and spacing_ok:
                new_text = prev_text + text
                new_score = min(prev_score, score)
                new_bbox = (
                    px1,
                    min(py1, y1),
                    x2,
                    max(py2, y2),
                )
                merged[-1].text = new_text
                merged[-1].confidence = new_score
                merged[-1].bbox = new_bbox
            else:
                merged.append(RawOCR(text=text, confidence=score, bbox=bbox))

        return merged

    def recognize(self, image: np.ndarray) -> List[RawOCR]:
        """
        공통 파이프라인
        OCR → bbox 병합 → RawOCR 리스트 생성
        """
        raw_results = self._recognize_raw(image)

        h, w = image.shape[:2]
        merged = self._merge_ocr_boxes(
            raw_results,
            y_center_ratio=self.y_center_ratio,
            min_height_ratio=self.min_height_ratio,
            max_spacing_ratio=self.max_spacing_ratio
        )

        return merged