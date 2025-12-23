import cv2
import numpy as np


# 색상 공간 변환 (Color Space Conversion) #################################

def to_grayscale(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

def to_hsv(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2HSV)


# 밝기 및 대비 보정 (Brightness & Contrast) #################################

def adjust_contrast_linear(img, alpha=1.5, beta=0):
    """
    선형적인 대비 및 밝기 조정
    alpha: 대비(1.0-3.0), beta: 밝기(0-100)
    """
    return cv2.convertScaleAbs(img, alpha=alpha, beta=beta)

def adjust_gamma(img, gamma=1.0):
    """감마 보정을 통한 비선형 밝기 조절 (gamma > 1.0 이면 밝아짐)"""
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype("uint8")
    return cv2.LUT(img, table)

def apply_clahe_color(img, clip_limit=3.0, tile_size=(8, 8)):
    """
    LAB 공간에서 명도(L/Y) 채널에만 CLAHE 적용하여 색상 왜곡 최소화하며 히스토그램 평활화
    """
    # LAB 색공간으로 변환 (L: 밝기, A/B: 색상)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    # 대비 제한 적응형 히스토그램 평활화 적용
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_size)
    l = clahe.apply(l)

    # 다시 합치기
    enhanced_lab = cv2.merge((l, a, b))
    return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

def apply_white_balance(img, p=0.5):
    """White Patch 가설 기반 자동 화이트 밸런스"""
    assert img.dtype == np.uint8
    out = img.astype(np.float32)

    for c in range(3):
        channel = out[:, :, c]
        low = np.percentile(channel, p)
        high = np.percentile(channel, 100 - p)

        if high > low:
            channel = (channel - low) / (high - low) * 255
        out[:, :, c] = channel

    return np.clip(out, 0, 255).astype(np.uint8)


# 이진화 및 필터링 (Binarization & Filtering) #################################
def binarize(img, threshold=127, inverse=False):
    """이미지 이진화 (그레이스케일 입력 권장)"""
    mode = cv2.THRESH_BINARY_INV if inverse else cv2.THRESH_BINARY
    _, binary_img = cv2.threshold(img, threshold, 255, mode)
    return binary_img

def binarize_adaptive(img, block_size=11, c=2):
    """조명 변화에 강한 적응형 이진화"""
    return cv2.adaptiveThreshold(
        img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, block_size, c
    )
