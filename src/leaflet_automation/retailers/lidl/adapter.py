from datetime import date
import re

from leaflet_automation.app.config import settings
from leaflet_automation.core.storage import leaflet_page_image_path, product_screenshot_path
from leaflet_automation.core.models import ExtractedProduct, Leaflet, LeafletPage
from leaflet_automation.retailers.base import RetailerAdapter
from leaflet_automation.retailers.lidl.api import LidlLeafletApi
from leaflet_automation.retailers.lidl.discovery import discover_leaflets
from leaflet_automation.retailers.lidl.filters import filter_target_leaflets, is_candidate_page
from leaflet_automation.retailers.lidl.parser import (
    extract_product_names_from_alt_text,
    extract_product_names_from_keywords,
    parse_leaflet,
)
from leaflet_automation.services.classifier import ProductClassifier, normalize_text
from leaflet_automation.services.images import ImageService
from leaflet_automation.services.ocr import OcrLine, OcrService
from leaflet_automation.services.screenshots import ScreenshotService


class LidlAdapter(RetailerAdapter):
    retailer = "lidl"

    def __init__(self) -> None:
        self.api = LidlLeafletApi()
        self.classifier = ProductClassifier()
        self.image_service = ImageService()
        self.ocr_service = OcrService()
        self.screenshot_service = ScreenshotService()

    def discover_leaflets(self, today: date) -> list[Leaflet]:
        return discover_leaflets(self.api)

    def get_leaflet(self, leaflet_id: str) -> Leaflet:
        return parse_leaflet(self.api.get_flyer(leaflet_id))

    def filter_target_leaflets(self, leaflets: list[Leaflet], today: date) -> list[Leaflet]:
        return filter_target_leaflets(leaflets, today)

    def find_candidate_pages(self, leaflet: Leaflet) -> list[LeafletPage]:
        return [page for page in leaflet.pages if is_candidate_page(page)]

    def extract_products_from_page(self, leaflet: Leaflet, page: LeafletPage) -> list[ExtractedProduct]:
        page_text = " ".join(part for part in [page.alt_text, page.keywords] if part)
        page_category = self.classifier.classify(page_text)
        produce_context = any(
            marker in normalize_text(page.alt_text or "")
            for marker in ("frutas", "fruta", "legumes", "frescos")
        )
        products: list[ExtractedProduct] = []

        for name in extract_product_names_from_alt_text(page.alt_text):
            category = self.classifier.classify(name)
            if category is None and produce_context:
                category = page_category
            if category is None:
                continue
            products.append(
                ExtractedProduct(
                    retailer=self.retailer,
                    leaflet_id=leaflet.id,
                    page_number=page.page_number,
                    program_type=leaflet.program_type,
                    category=category,
                    name=name,
                    promo_start=leaflet.offer_start_date,
                    promo_end=leaflet.offer_end_date,
                    raw_text=page.alt_text or "",
                    confidence=0.8,
                )
            )

        for name in extract_product_names_from_keywords(page.keywords):
            category = self.classifier.classify(name)
            if category is None:
                continue
            products.append(
                ExtractedProduct(
                    retailer=self.retailer,
                    leaflet_id=leaflet.id,
                    page_number=page.page_number,
                    program_type=leaflet.program_type,
                    category=category,
                    name=name,
                    promo_start=leaflet.offer_start_date,
                    promo_end=leaflet.offer_end_date,
                    raw_text=page.keywords or "",
                    confidence=0.55,
                )
            )

        if products:
            self._attach_screenshots(leaflet, page, products)

        return products

    def _attach_screenshots(
        self,
        leaflet: Leaflet,
        page: LeafletPage,
        products: list[ExtractedProduct],
    ) -> None:
        image_url = page.zoom_url or page.image_url
        if not image_url:
            return

        image_path = leaflet_page_image_path(settings.data_dir, leaflet, page)
        self.api.download_binary(image_url, image_path)
        page.local_image_path = image_path
        ocr_lines = self.ocr_service.extract_lines(image_path)
        self._attach_prices(products, ocr_lines)
        boxes = self.image_service.detect_product_blocks(image_path, expected_blocks=len(products))
        for index, product in enumerate(products):
            box = boxes[min(index, len(boxes) - 1)]
            screenshot_path = product_screenshot_path(settings.data_dir, product, index=index)
            self.screenshot_service.crop(image_path, box, screenshot_path)
            product.screenshot_path = screenshot_path

    def _attach_prices(self, products: list[ExtractedProduct], ocr_lines: list[OcrLine]) -> None:
        for product in products:
            label_line = self._match_product_label(product.name, ocr_lines)
            if label_line is None:
                continue
            price_line = self._match_price_line(label_line, ocr_lines)
            if price_line is None:
                continue

            product.price_text = price_line.text.replace(".", ",")
            product.price_value = float(price_line.text.replace(",", "."))
            product.raw_text = f"{product.raw_text}\nOCR: {label_line.text} | {price_line.text}"

    def _match_product_label(self, product_name: str, ocr_lines: list[OcrLine]) -> OcrLine | None:
        tokens = [token for token in normalize_text(product_name).split() if len(token) > 2]
        if not tokens:
            return None

        best_line: OcrLine | None = None
        best_score = 0.0
        for line in ocr_lines:
            normalized_line = normalize_text(line.text)
            token_hits = sum(
                1
                for token in tokens
                if token in normalized_line or token.rstrip("s") in normalized_line
            )
            if token_hits == 0:
                continue
            score = token_hits / len(tokens)
            if normalized_line.replace(" ", "").startswith(normalize_text(product_name).replace(" ", "")):
                score += 0.5
            if score > best_score:
                best_score = score
                best_line = line

        return best_line

    def _match_price_line(self, label_line: OcrLine, ocr_lines: list[OcrLine]) -> OcrLine | None:
        candidates: list[tuple[float, OcrLine]] = []
        for line in ocr_lines:
            match = re.search(r"(?<!\d)(\d+[\.,]\d{2})(?!\d)", line.text)
            if match is None:
                continue
            normalized_line = normalize_text(line.text)
            if "kg=" in normalized_line or "n°" in normalized_line or "n9" in normalized_line:
                continue
            if abs(line.center_y - label_line.center_y) > 220:
                continue

            dx = line.left - label_line.right
            if dx < -120:
                continue
            penalty = max(dx, 0) + abs(line.center_y - label_line.center_y) * 2
            candidates.append((penalty, line))

        if not candidates:
            return None

        candidates.sort(key=lambda item: item[0])
        return candidates[0][1]

    def close(self) -> None:
        self.api.close()
