from pathlib import Path

from PIL import Image


class ScreenshotService:
    def crop(self, image_path: Path, box: tuple[int, int, int, int], output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(image_path) as image:
            cropped = image.crop(box)
            cropped.save(output_path)
        return output_path
