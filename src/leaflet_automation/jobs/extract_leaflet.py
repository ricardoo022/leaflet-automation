from leaflet_automation.core.models import ExtractedProduct, Leaflet
from leaflet_automation.retailers.lidl.adapter import LidlAdapter


def extract_lidl_leaflet(leaflet: Leaflet) -> list[ExtractedProduct]:
    adapter = LidlAdapter()
    try:
        products: list[ExtractedProduct] = []
        for page in adapter.find_candidate_pages(leaflet):
            products.extend(adapter.extract_products_from_page(leaflet, page))
        return products
    finally:
        adapter.close()
