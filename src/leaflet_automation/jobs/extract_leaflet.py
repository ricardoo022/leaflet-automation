from dataclasses import dataclass

from leaflet_automation.app.config import settings
from leaflet_automation.core.dedupe import dedupe_products
from leaflet_automation.core.models import ExtractedProduct, Leaflet
from leaflet_automation.db.repositories.leaflets import LeafletRepository
from leaflet_automation.db.repositories.products import ProductRepository
from leaflet_automation.db.schema import initialize_schema
from leaflet_automation.db.sqlite import connect
from leaflet_automation.retailers.lidl.adapter import LidlAdapter


@dataclass
class ExtractionResult:
    leaflet: Leaflet
    candidate_pages: int
    extracted_products: int
    persisted_products: int


def extract_lidl_leaflet(leaflet: Leaflet) -> list[ExtractedProduct]:
    adapter = LidlAdapter()
    try:
        products: list[ExtractedProduct] = []
        for page in adapter.find_candidate_pages(leaflet):
            products.extend(adapter.extract_products_from_page(leaflet, page))
        return products
    finally:
        adapter.close()


def run_lidl_extraction(leaflet_id: str) -> ExtractionResult:
    adapter = LidlAdapter()
    connection = connect(settings.database_path)
    initialize_schema(connection)

    try:
        leaflet_repository = LeafletRepository(connection)
        leaflet = leaflet_repository.get_by_id(leaflet_id)
        if leaflet is None:
            raise LookupError(f"Leaflet {leaflet_id} was not found in the database. Run discovery first.")

        if not leaflet.pages:
            # Older discoveries may have leaflet headers but no persisted pages yet.
            refreshed_leaflet = adapter.get_leaflet(leaflet_id)
            refreshed_leaflet.program_type = leaflet.program_type
            leaflet_repository.upsert_many([refreshed_leaflet])
            leaflet = refreshed_leaflet

        candidate_pages = adapter.find_candidate_pages(leaflet)

        products: list[ExtractedProduct] = []
        for page in candidate_pages:
            products.extend(adapter.extract_products_from_page(leaflet, page))

        unique_products = dedupe_products(products)
        product_repository = ProductRepository(connection)
        product_repository.delete_by_leaflet_id(leaflet_id)
        if unique_products:
            product_repository.insert_many(unique_products)

        return ExtractionResult(
            leaflet=leaflet,
            candidate_pages=len(candidate_pages),
            extracted_products=len(products),
            persisted_products=len(unique_products),
        )
    finally:
        adapter.close()
        connection.close()
