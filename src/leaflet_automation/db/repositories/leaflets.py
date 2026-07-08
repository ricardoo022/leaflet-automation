import sqlite3

from leaflet_automation.core.enums import ProgramType
from leaflet_automation.core.models import Leaflet, LeafletPage


class LeafletRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get_by_id(self, leaflet_id: str) -> Leaflet | None:
        row = self.connection.execute(
            "SELECT * FROM leaflets WHERE id = ?",
            (leaflet_id,),
        ).fetchone()
        if row is None:
            return None

        return Leaflet(
            id=row["id"],
            retailer=row["retailer"],
            name=row["name"],
            title=row["title"],
            category=row["category"],
            subcategory=row["subcategory"],
            status=row["status"],
            program_type=ProgramType(row["program_type"]),
            start_date=row["start_date"],
            end_date=row["end_date"],
            offer_start_date=row["offer_start_date"],
            offer_end_date=row["offer_end_date"],
            url=row["url"],
            pdf_url=row["pdf_url"],
            high_res_pdf_url=row["high_res_pdf_url"],
            thumbnail_url=row["thumbnail_url"],
            pages=self._get_pages(leaflet_id),
        )

    def upsert_many(self, leaflets: list[Leaflet]) -> None:
        if not leaflets:
            return

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
        self.connection.executemany(
            "DELETE FROM leaflet_pages WHERE leaflet_id = ?",
            [(leaflet.id,) for leaflet in leaflets],
        )
        self.connection.executemany(
            """
            INSERT INTO leaflet_pages (
                leaflet_id, page_number, image_url, zoom_url, thumbnail_url, alt_text, keywords
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    page.leaflet_id,
                    page.page_number,
                    page.image_url,
                    page.zoom_url,
                    page.thumbnail_url,
                    page.alt_text,
                    page.keywords,
                )
                for leaflet in leaflets
                for page in leaflet.pages
            ],
        )
        self.connection.commit()

    def _get_pages(self, leaflet_id: str) -> list[LeafletPage]:
        rows = self.connection.execute(
            "SELECT * FROM leaflet_pages WHERE leaflet_id = ? ORDER BY page_number",
            (leaflet_id,),
        ).fetchall()
        return [
            LeafletPage(
                leaflet_id=row["leaflet_id"],
                page_number=row["page_number"],
                image_url=row["image_url"],
                zoom_url=row["zoom_url"],
                thumbnail_url=row["thumbnail_url"],
                alt_text=row["alt_text"],
                keywords=row["keywords"],
            )
            for row in rows
        ]
