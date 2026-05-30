import sqlite3

from leaflet_automation.core.models import ExtractedProduct


class ProductRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def insert_many(self, products: list[ExtractedProduct]) -> None:
        self.connection.executemany(
            """
            INSERT INTO products (
                retailer, leaflet_id, page_number, program_type, category, name,
                price_text, price_value, promo_start, promo_end, screenshot_path,
                raw_text, confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    product.retailer,
                    product.leaflet_id,
                    product.page_number,
                    product.program_type.value,
                    product.category,
                    product.name,
                    product.price_text,
                    product.price_value,
                    product.promo_start.isoformat() if product.promo_start else None,
                    product.promo_end.isoformat() if product.promo_end else None,
                    str(product.screenshot_path) if product.screenshot_path else None,
                    product.raw_text,
                    product.confidence,
                )
                for product in products
            ],
        )
        self.connection.commit()
