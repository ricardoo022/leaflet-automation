from datetime import date

from leaflet_automation.core.models import ExtractedProduct, Leaflet, LeafletPage
from leaflet_automation.retailers.base import RetailerAdapter
from leaflet_automation.retailers.lidl.api import LidlLeafletApi
from leaflet_automation.retailers.lidl.discovery import discover_leaflets
from leaflet_automation.retailers.lidl.filters import filter_target_leaflets, is_candidate_page


class LidlAdapter(RetailerAdapter):
    retailer = "lidl"

    def __init__(self) -> None:
        self.api = LidlLeafletApi()

    def discover_leaflets(self, today: date) -> list[Leaflet]:
        return discover_leaflets(self.api)

    def filter_target_leaflets(self, leaflets: list[Leaflet], today: date) -> list[Leaflet]:
        return filter_target_leaflets(leaflets, today)

    def find_candidate_pages(self, leaflet: Leaflet) -> list[LeafletPage]:
        return [page for page in leaflet.pages if is_candidate_page(page)]

    def extract_products_from_page(self, leaflet: Leaflet, page: LeafletPage) -> list[ExtractedProduct]:
        raise NotImplementedError("Implement OCR and product block extraction here.")

    def close(self) -> None:
        self.api.close()
