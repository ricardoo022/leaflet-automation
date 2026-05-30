from abc import ABC, abstractmethod
from datetime import date

from leaflet_automation.core.models import ExtractedProduct, Leaflet, LeafletPage


class RetailerAdapter(ABC):
    retailer: str

    @abstractmethod
    def discover_leaflets(self, today: date) -> list[Leaflet]:
        raise NotImplementedError

    @abstractmethod
    def filter_target_leaflets(self, leaflets: list[Leaflet], today: date) -> list[Leaflet]:
        raise NotImplementedError

    @abstractmethod
    def find_candidate_pages(self, leaflet: Leaflet) -> list[LeafletPage]:
        raise NotImplementedError

    @abstractmethod
    def extract_products_from_page(self, leaflet: Leaflet, page: LeafletPage) -> list[ExtractedProduct]:
        raise NotImplementedError
