from pathlib import Path


class ScreenshotService:
    def crop(self, image_path: Path, box: tuple[int, int, int, int], output_path: Path) -> Path:
        raise NotImplementedError("Wire Pillow/OpenCV cropping here during implementation.")
