from typing import Optional
import numpy as np
from vision.utils.verifier import is_plate_like, plate_similarity
from vision.result import PlateResult
from vision.utils.image_proc import apply_clahe_color


class PlateNumberDetector:

    def __init__(
            self,
            *,
            model: str = "paddle",
            plate_similarity_thresh: float = 80,
            apply_preprocess: bool = True,
            ocr_params: Optional[dict] = None,
            **engine_kwargs,
    ):
        self.apply_preprocess = apply_preprocess
        self.plate_similarity_thresh = plate_similarity_thresh
        ocr_params = ocr_params or {}

        if model == "paddle":
            try:
                from vision.engines.paddle import PaddleOCREngine
                self.engine = PaddleOCREngine(**ocr_params, **engine_kwargs)
            except Exception as e:
                raise RuntimeError(
                    f"It appears that the required environment for PaddleOCR has not been set up correctly. \
                    Please check the compatibility of your environment by referring to the following link: \
                    https://github.com/PaddlePaddle/PaddleOCR")

        elif model == "clova":
            from vision.engines.clova import ClovaOCREngine
            self.engine = ClovaOCREngine(**ocr_params, **engine_kwargs)
        else:
            raise ValueError(f"Unsupported OCR model: {model} (support only 'paddle', 'clova'")

    def detect(self, frame: np.ndarray, target: str = '') -> Optional[PlateResult]:
        img = frame.copy()

        # 전처리
        if self.apply_preprocess:
            img = apply_clahe_color(img)

        # OCR
        ocr_result = self.engine.recognize(img)

        # 타겟 번호판과의 유사도 측정
        plates = []
        target_plate = None
        best_similarity = 0

        for res in ocr_result:
            res.text = res.text.replace(' ', '')
            if not is_plate_like(res.text):
                continue

            similarity = plate_similarity(target, res.text)
            plate = PlateResult(text=res.text, similarity=similarity, bbox=res.bbox)
            plates.append(plate)
            print(target, res.text, similarity, sep=' | ')

            if similarity < self.plate_similarity_thresh:
                continue
            if similarity > best_similarity:
                best_similarity = similarity
                target_plate = plate

        print('찾은 타겟 번호판')
        print(target_plate)
        print('유사도 점수:', best_similarity)

        return target_plate
