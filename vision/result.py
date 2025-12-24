from dataclasses import dataclass
from typing import Tuple, Optional
import numpy as np

@dataclass
class RawOCR:
    text: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)

@dataclass
class PlateResult:
    text: str
    similarity: float
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)


@dataclass
class ColorRecognitionResult:
    color: str
    area_ratio: float
    center_y: int = 0
    mask: Optional[np.ndarray] = None
