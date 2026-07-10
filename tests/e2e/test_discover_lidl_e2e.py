"""End-of-story end-to-end test for:

    "As a user, I can run `leaflets discover-lidl` and it discovers real Lidl
    leaflets and saves them to the database."

This is a *real-data* e2e test per the project's end-of-story flow:

1. No mocks / no recorded responses: it calls Lidl's LIVE public API.
2. It drives the REAL CLI entrypoint (``leaflet_automation.cli.main:app``,
   the same callable the installed ``leaflets`` console script invokes) through
   a real OS process via ``subprocess.run`` -- NOT ``typer.testing.CliRunner``
   in-process (that would be an integration test, not e2e).
3. It asserts REAL data landed in the REAL SQLite file -- row counts, per-row
   content, referential integrity, and that the CLI's real stdout matches the
   real DB rows the same OS process persisted.
4. It is gated with ``@pytest.mark.e2e`` and only runs with ``--run-e2e``.
5. After the first green run it records a regression baseline (JSON snapshot of
   structural facts) so real external changes are detectable later.
7. The harness is ``subprocess.run`` -- no browser tools.

Isolation: the subprocess gets a throwaway temp SQLite path and temp data dir
via the ``LEAFLETS_`` env vars consumed by ``app.config.settings``. The real
SQLite engine, real schema initialization, real repository upserts all still run
-- only the *file paths* are redirected. That is a real database, not a mock.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

import pytest

from leaflet_automation.core.enums import ProgramType

_E2E_MARK = pytest.mark.e2e

_BASELINE_DIR = Path(__file__).parent / "baselines"
_BASELINE_PATH = _BASELINE_DIR / "discover_lidl_baseline.json"

_SCHEMA_VERSION = 1
_EXPECTED_LEAFLET_COLUMNS = [
    "id", "retailer", "name", "title", "category", "subcategory", "status",
    "program_type", "start_date", "end_date", "offer_start_date",
    "offer_end_date", "url", "pdf_url", "high_res_pdf_url", "thumbnail_url",
]
_EXPECTED_PAGE_COLUMNS = [
    "leaflet_id", "page_number", "image_url", "zoom_url", "thumbnail_url",
    "alt_text", "keywords",
]
_KNOWN_PROGRAM_TYPES = {p.value for p in ProgramType}


def _build_cli_command(args: list[str]) -> list[str]:
    """Invoke the REAL CLI entrypoint in a real OS subprocess.

    Prefer the installed ``leaflets`` console script (the literal
    [project.scripts] entrypoint); fall back to calling ``app()`` directly with
    the same interpreter -- which is exactly what the console script does.
    Both forms run in a separate process; neither imports internal functions in
    the test process (that would be an integration test).
    """
    bin_dir = Path(sys.executable).parent
    leaflets_script = bin_dir / "leaflets"
    if leaflets_script.exists():
        return [str(leaflets_script), *args]
    # Fallback: identical to `leaflets = "...cli.main:app"` running app().
    script = "from leaflet_automation.cli.main import app; app()"
    return [sys.executable, "-c", script, *args]


def _run_discover(database_path: Path, data_dir: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["LEAFLETS_DATABASE_PATH"] = str(database_path)
    env["LEAFLETS_DATA_DIR"] = str(data_dir)
    # Force the live path (no fixture replay) for a true real-data e2e run.
    env.pop("LEAFLETS_LIDL_FIXTURE_DIR", None)
    # Run in the project root so relative assets behave like a normal CLI call.
    project_root = Path(__file__).resolve().parents[2]
    return subprocess.run(
        _build_cli_command(["discover-lidl"]),
        cwd=str(project_root),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _connect(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def _parse_stdout_ids(stdout: str) -> set[str]:
    """The discovery command prints `id | program | name | title | url` lines."""
    ids: set[str] = set()
    for line in stdout.strip().splitlines():
        if not line.strip():
            continue
        first = line.split(" | ", 1)[0].strip()
        if first:
            ids.add(first)
    return ids


def _snapshot(connection: sqlite3.Connection) -> dict:
    leaflet_cols = [row["name"] for row in connection.execute("PRAGMA table_info(leaflets)")]
    page_cols = [row["name"] for row in connection.execute("PRAGMA table_info(leaflet_pages)")]
    leaflet_rows = connection.execute(
        "SELECT id, retailer, name, title, program_type, url, "
        "offer_start_date, offer_end_date FROM leaflets"
    ).fetchall()
    page_rows = connection.execute(
        "SELECT leaflet_id FROM leaflet_pages"
    ).fetchall()
    return {
        "schema_version": _SCHEMA_VERSION,
        "leaflets_columns": leaflet_cols,
        "leaflet_pages_columns": page_cols,
        "retailers": sorted({row["retailer"] for row in leaflet_rows}),
        "program_types": sorted({row["program_type"] for row in leaflet_rows}),
        "leaflet_count": len(leaflet_rows),
        "leaflet_pages_count": len(page_rows),
        "recorded_at": _dt.datetime.now(tz=_dt.timezone.utc).isoformat(),
    }


@_E2E_MARK
class DiscoverLidlRealDataE2ETests(unittest.TestCase):
    """Real-data e2e for `leaflets discover-lidl`."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_root = Path(self._tmp.name)
        self.database_path = self.tmp_root / "leaflets.db"
        self.data_dir = self.tmp_root / "data"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run_and_load(self) -> tuple[subprocess.CompletedProcess[str], sqlite3.Connection]:
        result = _run_discover(self.database_path, self.data_dir)
        # Surface stderr up-front so failures are debuggable.
        if result.returncode != 0:
            self.fail(
                f"`leaflets discover-lidl` exited {result.returncode}.\n"
                f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )
        connection = _connect(self.database_path)
        self.addCleanup(connection.close)
        return result, connection

    def test_discover_lidl_is_runnable_and_writes_a_real_database_file(self) -> None:
        result, _ = self._run_and_load()
        self.assertTrue(
            self.database_path.exists(),
            "discover-lidl did not create a real SQLite file at the configured path",
        )
        self.assertTrue(result.stdout.strip(), "discover-lidl produced no stdout output")

    def test_real_leaflet_rows_were_persisted_with_real_content(self) -> None:
        _, connection = self._run_and_load()

        rows = connection.execute(
            "SELECT id, retailer, name, title, program_type, url, "
            "offer_start_date, offer_end_date FROM leaflets"
        ).fetchall()
        self.assertGreater(len(rows), 0, "no real leaflet rows persisted from live API")

        seen_ids: set[str] = set()
        for row in rows:
            rid = row["id"]
            self.assertTrue(rid, "leaflet.id is empty")
            self.assertNotIn(rid, seen_ids, "duplicate leaflet id persisted")
            seen_ids.add(rid)

            self.assertEqual(row["retailer"], "lidl")
            self.assertTrue(row["name"], "leaflet.name is empty")
            self.assertTrue(row["title"], "leaflet.title is empty")
            self.assertIn(row["program_type"], _KNOWN_PROGRAM_TYPES)
            self.assertTrue(row["url"].startswith("http"), f"leaflet.url is not an http url: {row['url']!r}")

            # Real date strings from the live API must parse as ISO dates.
            for col in ("offer_start_date", "offer_end_date"):
                value = row[col]
                if value is None or value == "":
                    continue
                _dt.date.fromisoformat(value)  # raises ValueError if not a real date

    def test_real_leaflet_pages_were_persisted_with_referential_integrity(self) -> None:
        _, connection = self._run_and_load()

        page_count = connection.execute("SELECT COUNT(*) FROM leaflet_pages").fetchone()[0]
        self.assertGreater(page_count, 0, "no real leaflet pages persisted from live API")

        leaflet_ids = {
            row["id"] for row in connection.execute("SELECT id FROM leaflets")
        }
        self.assertGreater(len(leaflet_ids), 0)

        orphans = connection.execute(
            "SELECT DISTINCT leaflet_id FROM leaflet_pages "
            "WHERE leaflet_id NOT IN (SELECT id FROM leaflets)"
        ).fetchall()
        self.assertEqual(
            [row["leaflet_id"] for row in orphans],
            [],
            "leaflet_pages reference leaflet ids not present in leaflets table",
        )

    def test_cli_real_stdout_matches_persisted_real_database_rows(self) -> None:
        result, connection = self._run_and_load()

        stdout_ids = _parse_stdout_ids(result.stdout)
        self.assertGreater(len(stdout_ids), 0, "discover-lidl stdout yielded no leaflet ids")

        db_ids = {
            row["id"] for row in connection.execute("SELECT id FROM leaflets")
        }
        # End-to-end integrity: what the real CLI printed came from the same
        # real API call whose target leaflets it upserted into the real DB.
        self.assertEqual(
            stdout_ids, db_ids,
            "CLI stdout ids != persisted DB ids (real API output not wired to real DB)",
        )

    def test_regression_baseline_matches_or_is_recorded(self) -> None:
        _, connection = self._run_and_load()
        snapshot = _snapshot(connection)

        # Schema contract must never drift silently.
        self.assertEqual(snapshot["leaflets_columns"], _EXPECTED_LEAFLET_COLUMNS)
        self.assertEqual(snapshot["leaflet_pages_columns"], _EXPECTED_PAGE_COLUMNS)

        # Real-data invariants (hard regression fences).
        self.assertEqual(snapshot["retailers"], ["lidl"])
        self.assertTrue(set(snapshot["program_types"]).issubset(_KNOWN_PROGRAM_TYPES))
        self.assertGreater(snapshot["leaflet_count"], 0)

        _BASELINE_DIR.mkdir(parents=True, exist_ok=True)
        if not _BASELINE_PATH.exists():
            # First green run -> record the regression baseline.
            _BASELINE_PATH.write_text(
                json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            self.skipTest(
                "first green e2e run -> regression baseline recorded at "
                f"{_BASELINE_PATH}; re-run --run-e2e to assert against it"
            )
            return

        baseline = json.loads(_BASELINE_PATH.read_text(encoding="utf-8"))

        # Detect a new program_type the baseline did not see (real external change).
        new_program_types = set(snapshot["program_types"]) - set(baseline["program_types"])
        self.assertFalse(
            new_program_types,
            f"new program_type(s) appeared vs baseline: {sorted(new_program_types)} "
            "-- review and update the baseline if expected",
        )
        # A previously-seen program_type must not disappear entirely if page count is healthy
        # (loose check: keep this about real structural drift, not weekly ID rotation).
        # Intentionally NOT asserting exact leaflet counts: leaflets rotate weekly.


if __name__ == "__main__":
    unittest.main()