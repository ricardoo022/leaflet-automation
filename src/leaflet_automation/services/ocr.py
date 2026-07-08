from dataclasses import dataclass
from pathlib import Path

from rapidocr_onnxruntime import RapidOCR


@dataclass
class OcrLine:
    text: str
    score: float
    left: int
    top: int
    right: int
    bottom: int

    @property
    def center_x(self) -> float:
        return (self.left + self.right) / 2

    @property
    def center_y(self) -> float:
        return (self.top + self.bottom) / 2


class OcrService:
    def __init__(self) -> None:
        self.engine = RapidOCR()

    def extract_text(self, image_path: Path) -> str:
        return " | ".join(line.text for line in self.extract_lines(image_path))

    def extract_lines(self, image_path: Path) -> list[OcrLine]:
        result, _ = self.engine(str(image_path))
        if not result:
            return []

        lines: list[OcrLine] = []
        for box, text, score in result:
            xs = [point[0] for point in box]
            ys = [point[1] for point in box]
            lines.append(
                OcrLine(
                    text=text,
                    score=float(score),
                    left=int(min(xs)),
                    top=int(min(ys)),
                    right=int(max(xs)),
                    bottom=int(max(ys)),
                )
            )
        return lines
