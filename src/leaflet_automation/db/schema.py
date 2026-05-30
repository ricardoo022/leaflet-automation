import sqlite3


def initialize_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS leaflets (
            id TEXT PRIMARY KEY,
            retailer TEXT NOT NULL,
            name TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT,
            subcategory TEXT,
            status TEXT,
            program_type TEXT NOT NULL,
            start_date TEXT,
            end_date TEXT,
            offer_start_date TEXT,
            offer_end_date TEXT,
            url TEXT NOT NULL,
            pdf_url TEXT,
            high_res_pdf_url TEXT,
            thumbnail_url TEXT
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            retailer TEXT NOT NULL,
            leaflet_id TEXT NOT NULL,
            page_number INTEGER NOT NULL,
            program_type TEXT NOT NULL,
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            price_text TEXT,
            price_value REAL,
            promo_start TEXT,
            promo_end TEXT,
            screenshot_path TEXT,
            raw_text TEXT NOT NULL,
            confidence REAL,
            FOREIGN KEY (leaflet_id) REFERENCES leaflets(id)
        );
        """
    )
    connection.commit()
