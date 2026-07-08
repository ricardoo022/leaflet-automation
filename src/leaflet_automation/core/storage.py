from pathlib import Path

from leaflet_automation.core.models import ExtractedProduct, Leaflet, LeafletPage


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def leaflet_directory(base_dir: Path, leaflet: Leaflet) -> Path:
    return ensure_directory(base_dir / leaflet.retailer / leaflet.id)


def leaflet_page_image_path(base_dir: Path, leaflet: Leaflet, page: LeafletPage) -> Path:
    folder = ensure_directory(base_dir / leaflet.retailer / leaflet.id / "pages")
    return folder / f"page-{page.page_number:02d}.png"


def product_screenshot_path(base_dir: Path, product: ExtractedProduct, index: int = 0) -> Path:
    safe_name = product.name.lower().replace(" ", "-")[:80]
    folder = ensure_directory(base_dir / product.retailer / product.leaflet_id / "products")
    suffix = f"-{index + 1:02d}" if index else ""
    return folder / f"page-{product.page_number:02d}-{safe_name}{suffix}.png"
