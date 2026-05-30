from pathlib import Path


class OcrService:
    def extract_text(self, image_path: Path) -> str:
        raise NotImplementedError("Wire pytesseract here during implementation.")
