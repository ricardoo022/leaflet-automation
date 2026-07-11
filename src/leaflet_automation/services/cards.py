from dataclasses import dataclass
from pathlib import Path

import cv2
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

    MIN_AREA_RATIO = 0.005
    MAX_AREA_RATIO = 0.50
    MIN_ASPECT = 0.2
    MAX_ASPECT = 5.0
    NMS_IOU = 0.3
    MORPH_KERNEL = 21
    ADAPTIVE_BLOCK = 51
    ADAPTIVE_C = 5

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

    def detect(self, image_path: Path) -> list[CardBox]:
        try:
            grid = self._grid_boxes(image_path)
        except (FileNotFoundError, OSError):
            grid = []
        if self._is_clean_grid(grid):
            return grid
        return self._contour_boxes(image_path)

    @staticmethod
    def _is_clean_grid(boxes: list[CardBox]) -> bool:
        if len(boxes) < 2:
            return False
        return len({b.x for b in boxes}) >= 2

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

    def _contour_boxes(self, image_path: Path) -> list[CardBox]:
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            return []
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h_img, w_img = gray.shape
        total_area = w_img * h_img
        if total_area == 0:
            return []

        thresh = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            self.ADAPTIVE_BLOCK,
            self.ADAPTIVE_C,
        )
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (self.MORPH_KERNEL, self.MORPH_KERNEL))
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        min_area = total_area * self.MIN_AREA_RATIO
        max_area = total_area * self.MAX_AREA_RATIO
        boxes: list[CardBox] = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            if area < min_area or area > max_area:
                continue
            aspect = w / h if h else 0.0
            if aspect < self.MIN_ASPECT or aspect > self.MAX_ASPECT:
                continue
            boxes.append(CardBox(x=int(x), y=int(y), w=int(w), h=int(h)))

        boxes = self._nms(boxes)
        return self._sort_tb_lr(boxes)

    @staticmethod
    def _sort_tb_lr(boxes: list[CardBox]) -> list[CardBox]:
        return sorted(boxes, key=lambda b: (b.y, b.x))

    @staticmethod
    def _iou(a: CardBox, b: CardBox) -> float:
        ix0 = max(a.x, b.x)
        iy0 = max(a.y, b.y)
        ix1 = min(a.x + a.w, b.x + b.w)
        iy1 = min(a.y + a.h, b.y + b.h)
        iw = max(0, ix1 - ix0)
        ih = max(0, iy1 - iy0)
        inter = iw * ih
        union = a.w * a.h + b.w * b.h - inter
        return inter / union if union else 0.0

    def _nms(self, boxes: list[CardBox]) -> list[CardBox]:
        if not boxes:
            return []
        order = sorted(boxes, key=lambda b: b.w * b.h, reverse=True)
        kept: list[CardBox] = []
        for box in order:
            if all(self._iou(box, k) < self.NMS_IOU for k in kept):
                kept.append(box)
        return kept
