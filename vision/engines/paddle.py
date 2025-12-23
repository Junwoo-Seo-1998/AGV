from vision.engines.base import OCRBase
from vision.result import RawOCR
from paddleocr import PaddleOCR
import pickle

class PaddleOCREngine(OCRBase):

    def __init__(self, **ocr_params):
        super().__init__(**ocr_params)
        self.model = None

        # 디버그 모드일 때는 모델 로드 생략
        if not self.debug_mode:

            # paddleocr 모델 로드
            self.model = PaddleOCR(
                lang="korean",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False
            )

    def _recognize_raw(self, image) -> [RawOCR]:

        result = []
        raw_res = None

        if self.debug_mode:
            pkl_path = "./data/demo/test1_paddle_res.pkl"
            with open(pkl_path, 'rb') as f:
                raw_res = pickle.load(f)
        else:
            raw_res = self.model.predict(image)
            if len(raw_res) == 0:
                return []
            raw_res = raw_res[0]


        texts = raw_res['rec_texts']
        scores = raw_res['rec_scores']
        polys = raw_res['rec_polys']

        if not texts or not scores or not polys:
            return []

        for i in range(len(texts)):
            vertices = polys[i]
            # 바운딩 박스 좌표 추출 (x, y)
            p1 = (int(vertices[0][0]), int(vertices[0][1]))  # 좌상단
            p3 = (int(vertices[2][0]), int(vertices[2][1]))  # 우하단

            result.append(RawOCR(
                text=texts[i],
                confidence=scores[i],
                bbox=(p1[0], p1[1], p3[0], p3[1])
            ))


        return result
