from pathlib import Path

from leaflet_automation.core.models import ExtractedProduct, Leaflet


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def leaflet_directory(base_dir: Path, leaflet: Leaflet) -> Path:
    return ensure_directory(base_dir / leaflet.retailer / leaflet.id)


def product_screenshot_path(base_dir: Path, product: ExtractedProduct) -> Path:
    safe_name = product.name.lower().replace(" ", "-")[:80]
    folder = ensure_directory(base_dir / product.retailer / product.leaflet_id / "products")
    return folder / f"page-{product.page_number:02d}-{safe_name}.png"
