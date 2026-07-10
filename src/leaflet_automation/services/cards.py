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
    def _grid_boxes(self, image_path: Path) -> list[CardBox]:
        with Image.open(image_path) as image:
            gray = image.convert("L")
        arr = np.asarray(gray)
        if arr.size == 0:
            return []
        row_bands = self._content_bands(arr.sum(axis=1), arr.shape[1])
        col_bands = self._content_bands(arr.sum(axis=0), arr.shape[0])
        if not row_bands or not col_bands:
            return []
        full_height = arr.shape[0]
        full_width = arr.shape[1]
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
                boxes.append(CardBox(x=x0, y=y0, w=x1 - x0, h=y1 - y0))
        return self._sort_tb_lr(boxes)

    def _content_bands(self, profile: np.ndarray, span: int) -> list[tuple[int, int]]:
        if profile.size == 0:
            return []
        threshold = float(profile.max()) * 0.08
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