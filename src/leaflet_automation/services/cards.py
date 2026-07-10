from dataclasses import dataclass
from pathlib import Path


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
        raise NotImplementedError