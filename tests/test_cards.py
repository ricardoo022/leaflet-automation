import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

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


def _make_solid_image(path: Path, size: tuple[int, int], fill: tuple[int, int, int]) -> None:
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


def _make_grid_image(path: Path) -> None:
    img = Image.new("RGB", (400, 400), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    card_w, card_h = 180, 180
    for row in range(2):
        for col in range(2):
            x0 = 10 + col * 200
            y0 = 10 + row * 200
            draw.rectangle(
                [x0, y0, x0 + card_w - 1, y0 + card_h - 1],
                fill=(30, 30, 30),
            )
    img.save(path)


def _make_contour_image(path: Path) -> None:
    img = Image.new("RGB", (600, 400), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, 170, 170], fill=(30, 30, 30))
    draw.rectangle([240, 30, 410, 160], fill=(30, 30, 30))
    draw.rectangle([450, 200, 580, 360], fill=(30, 30, 30))
    img.save(path)


class GridDetectorSyntheticTests(unittest.TestCase):
    def test_detects_four_cells_in_2x2_grid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "grid.png"
            _make_grid_image(p)
            boxes = CardDetector()._grid_boxes(p)
        self.assertEqual(len(boxes), 4)
        xs = sorted({b.x for b in boxes})
        ys = sorted({b.y for b in boxes})
        self.assertEqual(len(xs), 2)
        self.assertEqual(len(ys), 2)

    def test_synthetic_grid_has_distinct_columns_not_full_width_strips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "grid.png"
            _make_grid_image(p)
            boxes = CardDetector()._grid_boxes(p)
        self.assertGreaterEqual(len({box.x for box in boxes}), 2)
        self.assertGreaterEqual(len({box.y for box in boxes}), 2)

    def test_boxes_are_sorted_top_to_bottom_left_to_right(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "grid.png"
            _make_grid_image(p)
            boxes = CardDetector()._grid_boxes(p)
        keys = [(b.y, b.x) for b in boxes]
        self.assertEqual(keys, sorted(keys))

    def test_boxes_do_not_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "grid.png"
            _make_grid_image(p)
            boxes = CardDetector()._grid_boxes(p)
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                overlap_x = max(0, min(a.x + a.w, b.x + b.w) - max(a.x, b.x))
                overlap_y = max(0, min(a.y + a.h, b.y + b.h) - max(a.y, b.y))
                self.assertEqual(overlap_x * overlap_y, 0)


@unittest.skipUnless(FIXTURE_PAGE04.exists(), "page-04 fixture missing")
class GridDetectorPage04Tests(unittest.TestCase):
    def test_returns_at_least_two_boxes_on_page04(self) -> None:
        boxes = CardDetector()._grid_boxes(FIXTURE_PAGE04)
        self.assertGreaterEqual(len(boxes), 2)

    def test_boxes_sorted_and_non_overlapping_on_page04(self) -> None:
        boxes = CardDetector()._grid_boxes(FIXTURE_PAGE04)
        keys = [(b.y, b.x) for b in boxes]
        self.assertEqual(keys, sorted(keys))
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                overlap_x = max(0, min(a.x + a.w, b.x + b.w) - max(a.x, b.x))
                overlap_y = max(0, min(a.y + a.h, b.y + b.h) - max(a.y, b.y))
                self.assertEqual(overlap_x * overlap_y, 0)

    def test_boxes_cover_large_share_of_page_area(self) -> None:
        boxes = CardDetector()._grid_boxes(FIXTURE_PAGE04)
        with Image.open(FIXTURE_PAGE04) as img:
            total = img.size[0] * img.size[1]
        covered = sum(b.w * b.h for b in boxes)
        self.assertGreater(covered / total, 0.40)


class ContourDetectorDegenerateTests(unittest.TestCase):
    def test_solid_white_image_returns_empty_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "white.png"
            _make_solid_image(p, (200, 200), (255, 255, 255))
            self.assertEqual(CardDetector()._contour_boxes(p), [])

    def test_solid_black_image_returns_empty_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "black.png"
            _make_solid_image(p, (200, 200), (0, 0, 0))
            self.assertEqual(CardDetector()._contour_boxes(p), [])

    def test_empty_image_does_not_raise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "tiny.png"
            _make_solid_image(p, (1, 1), (255, 255, 255))
            result = CardDetector()._contour_boxes(p)
            self.assertIsInstance(result, list)

    def test_missing_file_returns_empty_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "does_not_exist.png"
            self.assertEqual(CardDetector()._contour_boxes(p), [])


class ContourDetectorSyntheticTests(unittest.TestCase):
    def test_detects_three_rectangles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "contours.png"
            _make_contour_image(p)
            boxes = CardDetector()._contour_boxes(p)
        self.assertGreaterEqual(len(boxes), 3)

    def test_boxes_sorted_top_to_bottom_left_to_right(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "contours.png"
            _make_contour_image(p)
            boxes = CardDetector()._contour_boxes(p)
        keys = [(b.y, b.x) for b in boxes]
        self.assertEqual(keys, sorted(keys))

    def test_boxes_do_not_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "contours.png"
            _make_contour_image(p)
            boxes = CardDetector()._contour_boxes(p)
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                overlap_x = max(0, min(a.x + a.w, b.x + b.w) - max(a.x, b.x))
                overlap_y = max(0, min(a.y + a.h, b.y + b.h) - max(a.y, b.y))
                self.assertEqual(overlap_x * overlap_y, 0)


@unittest.skipUnless(FIXTURE_PAGE04.exists(), "page-04 fixture missing")
class ContourDetectorPage04Tests(unittest.TestCase):
    def test_page04_yields_at_least_two_boxes(self) -> None:
        boxes = CardDetector()._contour_boxes(FIXTURE_PAGE04)
        self.assertGreaterEqual(len(boxes), 2)

    def test_page04_boxes_sorted_and_non_overlapping(self) -> None:
        boxes = CardDetector()._contour_boxes(FIXTURE_PAGE04)
        keys = [(b.y, b.x) for b in boxes]
        self.assertEqual(keys, sorted(keys))
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                overlap_x = max(0, min(a.x + a.w, b.x + b.w) - max(a.x, b.x))
                overlap_y = max(0, min(a.y + a.h, b.y + b.h) - max(a.y, b.y))
                self.assertEqual(overlap_x * overlap_y, 0)

    def test_page04_has_at_least_two_distinct_columns(self) -> None:
        boxes = CardDetector()._contour_boxes(FIXTURE_PAGE04)
        self.assertGreaterEqual(len({box.x for box in boxes}), 2)


class DetectUnifiedTests(unittest.TestCase):
    def test_detect_returns_grid_boxes_for_clean_synthetic_grid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "grid.png"
            _make_grid_image(p)
            boxes = CardDetector().detect(p)
        self.assertEqual(len(boxes), 4)
        self.assertGreaterEqual(len({b.x for b in boxes}), 2)

    @unittest.skipUnless(FIXTURE_PAGE04.exists(), "page-04 fixture missing")
    def test_detect_falls_back_to_contour_on_page04(self) -> None:
        boxes = CardDetector().detect(FIXTURE_PAGE04)
        self.assertIsInstance(boxes, list)
        self.assertGreaterEqual(len(boxes), 2)
        self.assertGreaterEqual(len({b.x for b in boxes}), 2)
        self.assertGreaterEqual(len({b.y for b in boxes}), 2)

    def test_detect_on_synthetic_contour_image_returns_boxes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "contours.png"
            _make_contour_image(p)
            boxes = CardDetector().detect(p)
        self.assertIsInstance(boxes, list)
        self.assertGreaterEqual(len(boxes), 1)

    def test_detect_does_not_raise_on_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "does_not_exist.png"
            result = CardDetector().detect(p)
        self.assertIsInstance(result, list)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
