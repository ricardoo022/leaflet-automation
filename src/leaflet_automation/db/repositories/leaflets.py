import sqlite3

from leaflet_automation.core.models import Leaflet


class LeafletRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def upsert_many(self, leaflets: list[Leaflet]) -> None:
        self.connection.executemany(
            """
            INSERT INTO leaflets (
                id, retailer, name, title, category, subcategory, status,
                program_type, start_date, end_date, offer_start_date, offer_end_date,
                url, pdf_url, high_res_pdf_url, thumbnail_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                retailer=excluded.retailer,
                name=excluded.name,
                title=excluded.title,
                category=excluded.category,
                subcategory=excluded.subcategory,
                status=excluded.status,
                program_type=excluded.program_type,
                start_date=excluded.start_date,
                end_date=excluded.end_date,
                offer_start_date=excluded.offer_start_date,
                offer_end_date=excluded.offer_end_date,
                url=excluded.url,
                pdf_url=excluded.pdf_url,
                high_res_pdf_url=excluded.high_res_pdf_url,
                thumbnail_url=excluded.thumbnail_url
            """,
            [
                (
                    leaflet.id,
                    leaflet.retailer,
                    leaflet.name,
                    leaflet.title,
                    leaflet.category,
                    leaflet.subcategory,
                    leaflet.status,
                    leaflet.program_type.value,
                    leaflet.start_date.isoformat() if leaflet.start_date else None,
                    leaflet.end_date.isoformat() if leaflet.end_date else None,
                    leaflet.offer_start_date.isoformat() if leaflet.offer_start_date else None,
                    leaflet.offer_end_date.isoformat() if leaflet.offer_end_date else None,
                    leaflet.url,
                    leaflet.pdf_url,
                    leaflet.high_res_pdf_url,
                    leaflet.thumbnail_url,
                )
                for leaflet in leaflets
            ],
        )
        self.connection.commit()
