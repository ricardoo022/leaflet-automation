import json
import unittest
from datetime import date
from pathlib import Path

from leaflet_automation.core.enums import ProgramType
from leaflet_automation.core.models import Leaflet, LeafletPage
from leaflet_automation.retailers.lidl.adapter import LidlAdapter
from leaflet_automation.retailers.lidl.parser import (
    extract_product_names_from_keywords,
    parse_leaflet,
)
from leaflet_automation.services.classifier import ProductClassifier

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "lidl"
PRODUCE_LEAFLET_ID = "019e6f22-4ece-7cf2-8ab3-6a958456e86a"


def _load_leaflet(leaflet_id: str) -> Leaflet:
    payload = json.loads((FIXTURE_DIR / f"{leaflet_id}.json").read_text(encoding="utf-8"))
    return parse_leaflet(payload)


class KeywordFallbackUnionTests(unittest.TestCase):
    def test_keyword_names_not_dropped_when_alt_text_yields_names(self) -> None:
        leaflet = _load_leaflet(PRODUCE_LEAFLET_ID)
        page = leaflet.pages[1]  # page-04 (produce)
        page.image_url = None
        page.zoom_url = None

        adapter = LidlAdapter()
        try:
            products = adapter.extract_products_from_page(leaflet, page)
        finally:
            adapter.close()

        classified_keyword_names = [
            name
            for name in extract_product_names_from_keywords(page.keywords)
            if ProductClassifier().classify(name) is not None
        ]
        keyword_origin = [product for product in products if product.confidence == 0.55]

        self.assertGreater(len(keyword_origin), 0)
        self.assertEqual([p.name for p in keyword_origin], classified_keyword_names)

        names = [p.name.casefold() for p in products]
        self.assertEqual(len(names), len(set(names)))

        alt_origin = [p.name.casefold() for p in products if p.confidence == 0.8]
        for alt_name in ("tomate cacho", "mirtilos", "maçã golden", "couve coração"):
            self.assertIn(alt_name, alt_origin)


if __name__ == "__main__":
    unittest.main()
