from leaflet_automation.core.models import ExtractedProduct, Leaflet


def dedupe_leaflets(leaflets: list[Leaflet]) -> list[Leaflet]:
    unique: dict[str, Leaflet] = {}
    for leaflet in leaflets:
        unique[leaflet.id] = leaflet
    return list(unique.values())


def dedupe_products(products: list[ExtractedProduct]) -> list[ExtractedProduct]:
    unique: dict[tuple[str, int, str, str], ExtractedProduct] = {}
    for product in products:
        key = (
            product.leaflet_id,
            product.page_number,
            product.name.strip().lower(),
            product.price_text or "",
        )
        unique[key] = product
    return list(unique.values())
