from vision.engines.base import OCRBase
from vision.result import RawOCR
import requests
import uuid
import time
import json
import os
from dotenv import load_dotenv
from io import BytesIO
from cv2 import imencode


class ClovaOCREngine(OCRBase):

    def __init__(self, **ocr_params):
        super().__init__(**ocr_params)

        # .env 파일 로드
        load_dotenv()
        self.api_url = os.environ["CLOVA_OCR_API_URL"]
        self.api_key = os.environ["CLOVA_OCR_API_KEY"]


    def _send_request(self, image_bytes: BytesIO) -> requests.Response:
        request_json = {
            'images': [{'format': 'jpg', 'name': 'demo'}],
            'requestId': str(uuid.uuid4()),
            'version': 'V2',
            "lang": "ko",
            'timestamp': int(round(time.time() * 1000))
        }

        payload = {
            'message': json.dumps(request_json).encode('UTF-8')
        }

        files = [
            ('file', ('plate.jpg', image_bytes, 'image/jpeg'))
        ]

        headers = {
            'X-OCR-SECRET': self.api_key
        }

        response = requests.request("POST", self.api_url, headers=headers, data=payload, files=files)
        return response


    def _recognize_raw(self, image) -> [RawOCR]:

        result = []
        raw_res = None

        # 디버그 모드: 사전 OCR 데이터 사용(API 호출 수 절약용)
        if self.debug_mode:
            json_path = "./data/demo/test1_clova_res.json"
            with open(json_path, 'r') as f:
                raw_res = json.load(f)

        # OCR API 호출
        else:
            # 이미지(ndarray) -> 요청에 첨부할 형식으로 변환
            success, encoded_img = imencode('.jpg', image)
            if not success:
                raise RuntimeError("Image encoding failed")
            image_bytes = BytesIO(encoded_img.tobytes())

            # api 요청
            try:
                response = self._send_request(image_bytes)
                raw_res = response.json()['images'][0]['fields']
            except Exception as e:
                raise RuntimeError("API call failed")

        # Clova OCR 응답 결과 -> RawOCR 형식으로
        for raw in raw_res:
            text = raw['inferText']
            vertices = raw['boundingPoly']['vertices']
            score = raw['inferConfidence']

            # 바운딩 박스 좌표 추출 (x, y)
            p1 = (int(vertices[0]['x']), int(vertices[0]['y']))  # 좌상단
            p3 = (int(vertices[2]['x']), int(vertices[2]['y']))  # 우하단

            result.append(RawOCR(
                text=text,
                confidence=score,
                bbox=(p1[0], p1[1], p3[0], p3[1])
            ))

        return result