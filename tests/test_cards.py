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


if __name__ == "__main__":
    unittest.main()