import re
from rapidfuzz import fuzz


def is_plate_like(text: str) -> bool:
    """
    번호판 인식 결과가 맞는지 텍스트 형식으로 판별
    """
    # 글자 오인식 고려해 가운데 한글 글자는
    # 한글 1자 또는 영어 1자 또는 숫자 1자인 경우까지 번호판으로 판별
    return bool(re.fullmatch(r'\d{3}[가-힣A-Za-z0-9]\d{4}', text))


def plate_similarity(target: str, ocr: str) -> float:
    """
    target 차량번호와 인식 결과 ocr이 얼마나 유사한지 유사도 측정
    """
    # 공백 제거
    target = target.replace(" ", "")
    ocr = ocr.replace(" ", "")

    if len(target) != 8 or len(ocr) != 8:
        return 0.0

    # 구간 분할
    t_front, t_mid, t_back = target[:3], target[3], target[4:]
    o_front, o_mid, o_back = ocr[:3], ocr[3], ocr[4:]

    front_score = fuzz.ratio(t_front, o_front)  # 앞 번호 유사도
    mid_score = fuzz.ratio(t_mid, o_mid)  # 가운데 글자 유사도
    back_score = fuzz.ratio(t_back, o_back)  # 뒷 번호 유사도

    # 앞/가운데/뒤 구성요소별 가중치 적용해 타겟과의 차량번호 유사도 집계
    score = (
            front_score * 0.45 +
            mid_score * 0.1 +
            back_score * 0.45
    )

    return score

