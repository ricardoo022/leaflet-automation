from pathlib import Path

from PIL import Image


class ImageService:
    def preprocess_for_ocr(self, image_path: Path) -> Path:
        return image_path

    def detect_product_blocks(
        self,
        image_path: Path,
        expected_blocks: int | None = None,
    ) -> list[tuple[int, int, int, int]]:
        with Image.open(image_path) as image:
            width, height = image.size

        if not expected_blocks or expected_blocks <= 1:
            return [(0, 0, width, height)]

        # Heuristic fallback: split the page vertically into equal review slices.
        block_height = max(1, height // expected_blocks)
        boxes: list[tuple[int, int, int, int]] = []
        for index in range(expected_blocks):
            top = index * block_height
            bottom = height if index == expected_blocks - 1 else min(height, (index + 1) * block_height)
            boxes.append((0, top, width, bottom))
        return boxes
