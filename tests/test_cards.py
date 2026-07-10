import unittest
from pathlib import Path

from leaflet_automation.services.cards import CardBox, CardDetector

FIXTURE_PAGE04 = (
    Path(__file__).resolve().parent.parent
    / "demo_screenshots"
    / "data"
    / "lidl"
    / "019e6f22-4ece-7cf2-8ab3-6a958456e86a"
    / "pages"
    / "page-04.png"
)


class CardBoxTests(unittest.TestCase):
    def test_center_properties(self) -> None:
        box = CardBox(x=10, y=20, w=100, h=40)
        self.assertEqual(box.cx, 60.0)
        self.assertEqual(box.cy, 40.0)

    def test_fields_are_ints(self) -> None:
        box = CardBox(x=1, y=2, w=3, h=4)
        self.assertEqual((box.x, box.y, box.w, box.h), (1, 2, 3, 4))


import tempfile


def _make_solid_image(path: Path, size: tuple[int, int], fill: tuple[int, int, int]) -> None:
    from PIL import Image
    Image.new("RGB", size, fill).save(path)


class GridDetectorDegenerateTests(unittest.TestCase):
    def test_solid_white_image_returns_empty_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "white.png"
            _make_solid_image(p, (200, 200), (255, 255, 255))
            self.assertEqual(CardDetector()._grid_boxes(p), [])

    def test_solid_black_image_returns_empty_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "black.png"
            _make_solid_image(p, (200, 200), (0, 0, 0))
            self.assertEqual(CardDetector()._grid_boxes(p), [])

    def test_empty_image_does_not_raise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "tiny.png"
            _make_solid_image(p, (1, 1), (255, 255, 255))
            result = CardDetector()._grid_boxes(p)
            self.assertIsInstance(result, list)


if __name__ == "__main__":
    unittest.main()