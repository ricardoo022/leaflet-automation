from pathlib import Path


class ImageService:
    def preprocess_for_ocr(self, image_path: Path) -> Path:
        raise NotImplementedError("Wire Pillow/OpenCV preprocessing here during implementation.")

    def detect_product_blocks(self, image_path: Path) -> list[tuple[int, int, int, int]]:
        raise NotImplementedError("Implement bounding-box detection for product blocks here.")
