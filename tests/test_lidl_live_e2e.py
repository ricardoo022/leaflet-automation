import logging
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from typer.testing import CliRunner

from leaflet_automation.app.config import settings
from leaflet_automation.cli.main import app
from leaflet_automation.retailers.lidl.adapter import LidlAdapter
from leaflet_automation.retailers.lidl.api import LidlLeafletApi


RUNNER = CliRunner()


class LidlLiveEndToEndTests(unittest.TestCase):
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
        settings.lidl_fixture_dir = None

    def tearDown(self) -> None:
        settings.database_path = self.previous_database_path
        settings.data_dir = self.previous_data_dir
        settings.lidl_fixture_dir = self.previous_fixture_dir
        self.temp_dir.cleanup()

    def test_live_listing_page_exposes_flyer_ids_and_live_payloads(self) -> None:
        api = LidlLeafletApi()
        try:
            flyer_ids = api.get_flyer_overview_ids()
            self.assertGreater(len(flyer_ids), 0)
            payload = api.get_flyer(flyer_ids[0])
        finally:
            api.close()

        self.assertEqual(payload["flyer"]["id"], flyer_ids[0])
        self.assertTrue(payload["flyer"].get("name"))
        self.assertGreater(len(payload["flyer"].get("pages", [])), 0)

    def test_live_cli_discover_lidl_populates_real_sqlite(self) -> None:
        result = RUNNER.invoke(app, ["discover-lidl"])

        self.assertEqual(result.exit_code, 0)
        self.assertTrue(result.stdout.strip())
        connection = sqlite3.connect(settings.database_path)
        try:
            persisted_count = connection.execute("SELECT COUNT(*) FROM leaflets").fetchone()[0]
            persisted_pages = connection.execute("SELECT COUNT(*) FROM leaflet_pages").fetchone()[0]
        finally:
            connection.close()

        self.assertGreater(persisted_count, 0)
        self.assertGreater(persisted_pages, persisted_count)

    def test_live_cli_discover_then_extract_creates_products_and_screenshots(self) -> None:
        discover_result = RUNNER.invoke(app, ["discover-lidl"])
        self.assertEqual(discover_result.exit_code, 0)

        connection = sqlite3.connect(settings.database_path)
        try:
            leaflet_ids = [
                row[0]
                for row in connection.execute("SELECT id FROM leaflets ORDER BY offer_start_date, id DESC").fetchall()
            ]
        finally:
            connection.close()

        adapter = LidlAdapter()
        try:
            chosen_leaflet_id: str | None = None
            for leaflet_id in leaflet_ids:
                leaflet = adapter.get_leaflet(leaflet_id)
                for page in adapter.find_candidate_pages(leaflet):
                    if adapter.extract_products_from_page(leaflet, page):
                        chosen_leaflet_id = leaflet_id
                        break
                if chosen_leaflet_id is not None:
                    break
        finally:
            adapter.close()

        self.assertIsNotNone(chosen_leaflet_id)
        assert chosen_leaflet_id is not None

        leaflet_output_dir = self.data_dir / "lidl" / chosen_leaflet_id
        if leaflet_output_dir.exists():
            shutil.rmtree(leaflet_output_dir)

        extract_result = RUNNER.invoke(app, ["extract-lidl", chosen_leaflet_id])
        self.assertEqual(extract_result.exit_code, 0)
        self.assertIn(chosen_leaflet_id, extract_result.stdout)
        self.assertIn("persisted=", extract_result.stdout)

        connection = sqlite3.connect(settings.database_path)
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(
                "SELECT name, price_value, screenshot_path FROM products WHERE leaflet_id = ? ORDER BY page_number, name",
                (chosen_leaflet_id,),
            ).fetchall()
        finally:
            connection.close()

        self.assertGreater(len(rows), 0)
        screenshot_paths = [Path(row["screenshot_path"]) for row in rows if row["screenshot_path"]]
        self.assertGreater(len(screenshot_paths), 0)
        self.assertTrue(all(path.exists() for path in screenshot_paths))

    def test_live_extract_works_from_persisted_snapshot_when_flyer_api_is_blocked(self) -> None:
        discover_result = RUNNER.invoke(app, ["discover-lidl"])
        self.assertEqual(discover_result.exit_code, 0)

        connection = sqlite3.connect(settings.database_path)
        try:
            leaflet_ids = [
                row[0]
                for row in connection.execute("SELECT id FROM leaflets ORDER BY offer_start_date, id DESC").fetchall()
            ]
        finally:
            connection.close()

        adapter = LidlAdapter()
        try:
            chosen_leaflet_id: str | None = None
            for leaflet_id in leaflet_ids:
                leaflet = adapter.get_leaflet(leaflet_id)
                for page in adapter.find_candidate_pages(leaflet):
                    if adapter.extract_products_from_page(leaflet, page):
                        chosen_leaflet_id = leaflet_id
                        break
                if chosen_leaflet_id is not None:
                    break
        finally:
            adapter.close()

        self.assertIsNotNone(chosen_leaflet_id)
        assert chosen_leaflet_id is not None

        previous_base_url = LidlLeafletApi.base_url
        LidlLeafletApi.base_url = "https://127.0.0.1:9/unreachable"
        try:
            extract_result = RUNNER.invoke(app, ["extract-lidl", chosen_leaflet_id])
        finally:
            LidlLeafletApi.base_url = previous_base_url

        self.assertEqual(extract_result.exit_code, 0)
        self.assertIn(chosen_leaflet_id, extract_result.stdout)


if __name__ == "__main__":
    unittest.main()
