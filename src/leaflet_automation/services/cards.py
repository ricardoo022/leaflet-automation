from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image


@dataclass
class CardBox:
    x: int
    y: int
    w: int
    h: int

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


class CardDetector:
    DARK_THRESHOLD = 200
    GAP_RATIO = 0.08

    def _grid_boxes(self, image_path: Path) -> list[CardBox]:
        with Image.open(image_path) as image:
            gray = image.convert("L")
        arr = np.asarray(gray)
        if arr.size == 0:
            return []

        dark = arr < self.DARK_THRESHOLD
        row_profile = dark.sum(axis=1).astype(np.float64)
        col_profile = dark.sum(axis=0).astype(np.float64)

        row_bands = self._content_bands(row_profile)
        col_bands = self._content_bands(col_profile)
        if not row_bands or not col_bands:
            return []

        full_height, full_width = arr.shape
        if (
            len(row_bands) == 1
            and row_bands[0][1] - row_bands[0][0] >= full_height * 0.98
            and len(col_bands) == 1
            and col_bands[0][1] - col_bands[0][0] >= full_width * 0.98
        ):
            return []

        boxes: list[CardBox] = []
        for y0, y1 in row_bands:
            for x0, x1 in col_bands:
                boxes.append(CardBox(x=int(x0), y=int(y0), w=int(x1 - x0), h=int(y1 - y0)))
        return self._sort_tb_lr(boxes)

    def _content_bands(self, profile: np.ndarray) -> list[tuple[int, int]]:
        if profile.size == 0:
            return []
        threshold = float(profile.max()) * self.GAP_RATIO
        if threshold <= 0:
            return []
        bands: list[tuple[int, int]] = []
        in_content = False
        start = 0
        for i, value in enumerate(profile):
            content = bool(value >= threshold)
            if content and not in_content:
                in_content = True
                start = i
            elif not content and in_content:
                bands.append((start, i))
                in_content = False
        if in_content:
            bands.append((start, int(profile.size)))
        return bands

    @staticmethod
    def _sort_tb_lr(boxes: list[CardBox]) -> list[CardBox]:
        return sorted(boxes, key=lambda b: (b.y, b.x))