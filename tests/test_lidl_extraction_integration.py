import json
import logging
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path

from typer.testing import CliRunner

from leaflet_automation.app.config import settings
from leaflet_automation.cli.main import app
from leaflet_automation.db.repositories.leaflets import LeafletRepository
from leaflet_automation.db.schema import initialize_schema
from leaflet_automation.db.sqlite import connect
from leaflet_automation.jobs.discover_leaflets import run_lidl_discovery
from leaflet_automation.jobs.extract_leaflet import run_lidl_extraction
from leaflet_automation.jobs.run_weekly import run_weekly_lidl
from leaflet_automation.retailers.lidl.adapter import LidlAdapter
from leaflet_automation.retailers.lidl.api import LidlLeafletApi
from leaflet_automation.retailers.lidl.filters import filter_target_leaflets, infer_program_type, is_candidate_page
from leaflet_automation.retailers.lidl.parser import (
    extract_product_names_from_alt_text,
    extract_product_names_from_keywords,
    parse_leaflet,
)
from leaflet_automation.services.ocr import OcrService


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "lidl"
RUNNER = CliRunner()


def load_fixture(leaflet_id: str) -> dict:
    fixture_path = FIXTURE_DIR / f"{leaflet_id}.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


class LidlExtractionIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "leaflets.db"
        self.data_dir = Path(self.temp_dir.name) / "data"
        self.previous_database_path = settings.database_path
        self.previous_data_dir = settings.data_dir
        self.previous_fixture_dir = settings.lidl_fixture_dir
        settings.database_path = self.database_path
        settings.data_dir = self.data_dir
        settings.lidl_fixture_dir = FIXTURE_DIR

    def tearDown(self) -> None:
        settings.database_path = self.previous_database_path
        settings.data_dir = self.previous_data_dir
        settings.lidl_fixture_dir = self.previous_fixture_dir
        self.temp_dir.cleanup()

    def seed_leaflet(self, leaflet_id: str) -> None:
        leaflet = parse_leaflet(load_fixture(leaflet_id))
        leaflet.program_type = infer_program_type(leaflet)
        connection = connect(settings.database_path)
        initialize_schema(connection)
        try:
            LeafletRepository(connection).upsert_many([leaflet])
        finally:
            connection.close()

    def test_parse_real_weekly_leaflet_maps_core_metadata_and_dates(self) -> None:
        leaflet = parse_leaflet(load_fixture("019e6f22-4ece-7cf2-8ab3-6a958456e86a"))

        self.assertEqual(leaflet.name, "Promoções")
        self.assertEqual(leaflet.title, "A partir de 01/06")
        self.assertEqual(leaflet.start_date, date(2026, 5, 29))
        self.assertEqual(leaflet.offer_start_date, date(2026, 6, 1))
        self.assertTrue(leaflet.pdf_url)
        self.assertTrue(leaflet.thumbnail_url)

    def test_parse_real_leaflet_preserves_page_numbers_and_media_urls(self) -> None:
        leaflet = parse_leaflet(load_fixture("019e4a4b-a039-7ba5-87b0-bca69e18d380"))

        self.assertEqual([page.page_number for page in leaflet.pages], [2, 4, 38])
        self.assertTrue(leaflet.pages[0].image_url)
        self.assertTrue(leaflet.pages[0].zoom_url)
        self.assertTrue(leaflet.pages[0].thumbnail_url)

    def test_parse_real_fixture_preserves_candidate_pages(self) -> None:
        leaflet = parse_leaflet(load_fixture("019e6f22-4ece-7cf2-8ab3-6a958456e86a"))

        self.assertEqual(leaflet.id, "019e6f22-4ece-7cf2-8ab3-6a958456e86a")
        self.assertEqual(len(leaflet.pages), 3)
        self.assertIn("tomate cacho", leaflet.pages[1].alt_text.lower())
        self.assertIn("mirtilo", leaflet.pages[1].keywords.lower())

    def test_extract_product_names_from_real_alt_text_produce_page(self) -> None:
        leaflet = parse_leaflet(load_fixture("019e6f22-4ece-7cf2-8ab3-6a958456e86a"))
        names = extract_product_names_from_alt_text(leaflet.pages[1].alt_text)

        self.assertEqual(names[:4], ["tomate cacho", "mirtilos", "maçã Golden", "couve coração"])

    def test_extract_product_names_from_real_keywords_fallback_text(self) -> None:
        leaflet = parse_leaflet(load_fixture("019e4a4b-a039-7ba5-87b0-bca69e18d380"))
        names = extract_product_names_from_keywords(leaflet.pages[1].keywords)

        self.assertGreaterEqual(len(names), 3)
        self.assertIn("Vale Mesmo Pera Vermelha", names)
        self.assertIn("Vermelha Tomate Chucha", names)

    def test_infer_program_type_from_real_weekly_payload(self) -> None:
        weekly_leaflet = parse_leaflet(load_fixture("019e6f27-3178-7eb7-a151-758e09e1eb07"))

        self.assertEqual(infer_program_type(weekly_leaflet).value, "weekly")

    def test_filter_target_leaflets_excludes_expired_real_fixture_for_reference_date(self) -> None:
        current = parse_leaflet(load_fixture("019e6f22-4ece-7cf2-8ab3-6a958456e86a"))
        novidades = parse_leaflet(load_fixture("019e6f27-3178-7eb7-a151-758e09e1eb07"))
        expired = parse_leaflet(load_fixture("019e4a4b-a039-7ba5-87b0-bca69e18d380"))

        filtered = filter_target_leaflets([current, novidades, expired], date(2026, 6, 2))

        self.assertEqual({leaflet.id for leaflet in filtered}, {current.id, novidades.id})

    def test_is_candidate_page_matches_real_produce_page_and_skips_non_target_page(self) -> None:
        produce_leaflet = parse_leaflet(load_fixture("019e6f22-4ece-7cf2-8ab3-6a958456e86a"))
        non_target_leaflet = parse_leaflet(load_fixture("019e6f27-3178-7eb7-a151-758e09e1eb07"))

        self.assertTrue(is_candidate_page(produce_leaflet.pages[1]))
        self.assertFalse(is_candidate_page(non_target_leaflet.pages[0]))

    def test_discover_leaflets_follows_real_related_flyers_and_dedupes(self) -> None:
        adapter = LidlAdapter()
        try:
            discovered = adapter.discover_leaflets(date(2026, 6, 2))
        finally:
            adapter.close()

        discovered_ids = [leaflet.id for leaflet in discovered]
        self.assertEqual(len(discovered_ids), 3)
        self.assertEqual(
            set(discovered_ids),
            {
                "019e6f22-4ece-7cf2-8ab3-6a958456e86a",
                "019e6f27-3178-7eb7-a151-758e09e1eb07",
                "019e4a4b-a039-7ba5-87b0-bca69e18d380",
            },
        )

    def test_leaflet_repository_upsert_and_get_by_id_round_trip_real_leaflet(self) -> None:
        leaflet_id = "019e6f22-4ece-7cf2-8ab3-6a958456e86a"
        self.seed_leaflet(leaflet_id)

        connection = connect(settings.database_path)
        initialize_schema(connection)
        try:
            stored = LeafletRepository(connection).get_by_id(leaflet_id)
        finally:
            connection.close()

        self.assertIsNotNone(stored)
        assert stored is not None
        self.assertEqual(stored.id, leaflet_id)
        self.assertEqual(stored.program_type.value, "weekly")
        self.assertEqual(stored.offer_start_date, date(2026, 6, 1))
        self.assertEqual([page.page_number for page in stored.pages], [2, 4, 30])
        self.assertIn("tomate cacho", (stored.pages[1].alt_text or "").lower())

    def test_run_lidl_discovery_persists_only_target_leaflets_to_real_sqlite(self) -> None:
        leaflets = run_lidl_discovery(today=date(2026, 6, 2))

        self.assertEqual(len(leaflets), 2)
        connection = sqlite3.connect(settings.database_path)
        try:
            persisted_count = connection.execute("SELECT COUNT(*) FROM leaflets").fetchone()[0]
            persisted_pages = connection.execute("SELECT COUNT(*) FROM leaflet_pages").fetchone()[0]
        finally:
            connection.close()

        self.assertEqual(persisted_count, 2)
        self.assertEqual(persisted_pages, sum(len(leaflet.pages) for leaflet in leaflets))

    def test_run_lidl_extraction_raises_lookup_error_for_unknown_leaflet_id(self) -> None:
        with self.assertRaises(LookupError):
            run_lidl_extraction("unknown-leaflet-id")

    def test_adapter_extract_products_from_real_candidate_page_attaches_categories_dates_and_screenshots(self) -> None:
        leaflet = parse_leaflet(load_fixture("019e6f22-4ece-7cf2-8ab3-6a958456e86a"))
        leaflet.program_type = infer_program_type(leaflet)
        page = leaflet.pages[1]
        adapter = LidlAdapter()
        try:
            products = adapter.extract_products_from_page(leaflet, page)
        finally:
            adapter.close()

        self.assertGreaterEqual(len(products), 4)
        self.assertTrue(all(product.category in {"frutas", "legumes"} for product in products))
        self.assertTrue(all(product.promo_start == leaflet.offer_start_date for product in products))
        self.assertTrue(all(product.screenshot_path is not None for product in products))
        self.assertTrue(all(product.screenshot_path.exists() for product in products if product.screenshot_path))
        prices = {product.name.lower(): product.price_value for product in products}
        self.assertEqual(prices["mirtilos"], 4.89)
        self.assertEqual(prices["tomate cacho"], 1.49)
        self.assertEqual(prices["maçã golden"], 1.19)
        self.assertEqual(prices["couve coração"], 0.99)

    def test_ocr_service_extracts_real_text_from_generated_screenshot(self) -> None:
        leaflet = parse_leaflet(load_fixture("019e6f22-4ece-7cf2-8ab3-6a958456e86a"))
        leaflet.program_type = infer_program_type(leaflet)
        page = leaflet.pages[1]
        adapter = LidlAdapter()
        try:
            products = adapter.extract_products_from_page(leaflet, page)
        finally:
            adapter.close()

        mirtilos = next(product for product in products if product.name.lower() == "mirtilos")
        ocr_text = OcrService().extract_text(mirtilos.screenshot_path)
        self.assertTrue(ocr_text)
        self.assertRegex(ocr_text, r"\d+\.\d{2}")

    def test_run_lidl_extraction_persists_real_products_without_duplicates(self) -> None:
        leaflet_id = "019e6f22-4ece-7cf2-8ab3-6a958456e86a"
        self.seed_leaflet(leaflet_id)

        first_result = run_lidl_extraction(leaflet_id)
        second_result = run_lidl_extraction(leaflet_id)

        self.assertGreaterEqual(first_result.candidate_pages, 2)
        self.assertGreater(first_result.persisted_products, 0)
        self.assertEqual(second_result.persisted_products, first_result.persisted_products)

        connection = sqlite3.connect(settings.database_path)
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(
                "SELECT name, category, screenshot_path FROM products WHERE leaflet_id = ? ORDER BY page_number, name",
                (leaflet_id,),
            ).fetchall()
        finally:
            connection.close()

        names = {row["name"] for row in rows}
        self.assertIn("tomate cacho", {name.lower() for name in names})
        self.assertIn("mirtilos", {name.lower() for name in names})
        self.assertIn("maçã Golden".lower(), {name.lower() for name in names})
        self.assertIn("cogumelos frescos", {name.lower() for name in names})

        categories = {row["category"] for row in rows}
        self.assertIn("frutas", categories)
        self.assertIn("legumes", categories)
        self.assertEqual(len(rows), first_result.persisted_products)
        screenshot_paths = [Path(row["screenshot_path"]) for row in rows if row["screenshot_path"]]
        self.assertTrue(all(path.exists() for path in screenshot_paths))
        self.assertTrue(any("products" in str(path) for path in screenshot_paths))

    def test_run_lidl_extraction_works_for_second_real_fixture(self) -> None:
        leaflet_id = "019e4a4b-a039-7ba5-87b0-bca69e18d380"
        self.seed_leaflet(leaflet_id)

        result = run_lidl_extraction(leaflet_id)

        self.assertGreaterEqual(result.candidate_pages, 2)
        self.assertGreater(result.persisted_products, 0)

        connection = sqlite3.connect(settings.database_path)
        connection.row_factory = sqlite3.Row
        try:
            names = {
                row["name"].lower()
                for row in connection.execute(
                    "SELECT name FROM products WHERE leaflet_id = ?",
                    (leaflet_id,),
                ).fetchall()
            }
        finally:
            connection.close()

        self.assertIn("pera vermelha", names)
        self.assertIn("tomate chucha", names)
        self.assertIn("cogumelos marron", names)
        screenshot_files = list((self.data_dir / "lidl" / leaflet_id / "products").glob("*.png"))
        self.assertGreater(len(screenshot_files), 0)
        connection = sqlite3.connect(settings.database_path)
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(
                "SELECT name, price_text, price_value FROM products WHERE leaflet_id = ? ORDER BY page_number, name",
                (leaflet_id,),
            ).fetchall()
        finally:
            connection.close()

        prices = {row["name"].lower(): row["price_value"] for row in rows if row["price_value"] is not None}
        self.assertGreaterEqual(len(prices), 3)
        self.assertEqual(prices["pera vermelha"], 2.49)
        self.assertEqual(prices["tomate chucha"], 1.59)
        self.assertEqual(prices["cogumelos marron"], 1.89)

    def test_run_lidl_extraction_uses_persisted_pages_when_flyer_api_is_unavailable(self) -> None:
        leaflet_id = "019e6f22-4ece-7cf2-8ab3-6a958456e86a"
        self.seed_leaflet(leaflet_id)
        previous_base_url = LidlLeafletApi.base_url
        LidlLeafletApi.base_url = "https://127.0.0.1:9/unreachable"
        try:
            result = run_lidl_extraction(leaflet_id)
        finally:
            LidlLeafletApi.base_url = previous_base_url

        self.assertGreaterEqual(result.candidate_pages, 2)
        self.assertGreater(result.persisted_products, 0)

    def test_cli_discover_lidl_prints_fixture_backed_leaflets_and_populates_db(self) -> None:
        result = RUNNER.invoke(app, ["discover-lidl"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("019e6f22-4ece-7cf2-8ab3-6a958456e86a", result.stdout)
        self.assertIn("019e6f27-3178-7eb7-a151-758e09e1eb07", result.stdout)

        connection = sqlite3.connect(settings.database_path)
        try:
            persisted_count = connection.execute("SELECT COUNT(*) FROM leaflets").fetchone()[0]
        finally:
            connection.close()

        self.assertEqual(persisted_count, 2)

    def test_cli_extract_lidl_prints_counts_and_persists_products(self) -> None:
        leaflet_id = "019e6f22-4ece-7cf2-8ab3-6a958456e86a"
        self.seed_leaflet(leaflet_id)

        result = RUNNER.invoke(app, ["extract-lidl", leaflet_id])

        self.assertEqual(result.exit_code, 0)
        self.assertIn(leaflet_id, result.stdout)
        self.assertIn("candidate-pages=3", result.stdout)
        self.assertIn("persisted=9", result.stdout)

        connection = sqlite3.connect(settings.database_path)
        try:
            product_count = connection.execute(
                "SELECT COUNT(*) FROM products WHERE leaflet_id = ?",
                (leaflet_id,),
            ).fetchone()[0]
        finally:
            connection.close()

        self.assertEqual(product_count, 9)

    def test_cli_extract_lidl_missing_leaflet_exits_1_with_lookup_message(self) -> None:
        result = RUNNER.invoke(app, ["extract-lidl", "missing-leaflet"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("missing-leaflet", result.stderr)

    def test_cli_run_weekly_lidl_reports_target_count_from_real_fixtures(self) -> None:
        result = RUNNER.invoke(app, ["run-weekly-lidl"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Discovered 2 target leaflets.", result.stdout)

    def test_run_weekly_lidl_returns_target_count_from_real_fixtures(self) -> None:
        self.assertEqual(run_weekly_lidl(today=date(2026, 6, 2)), 2)


if __name__ == "__main__":
    unittest.main()
