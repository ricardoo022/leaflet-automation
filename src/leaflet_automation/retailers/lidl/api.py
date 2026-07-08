import json
import re
from datetime import date
from pathlib import Path

import httpx

from leaflet_automation.app.config import settings


class LidlLeafletApi:
    base_url = "https://endpoints.leaflets.schwarz/v4"
    listing_page_url = "https://www.lidl.pt/c/folhetos/s10020672"

    def __init__(self) -> None:
        self.client = httpx.Client(
            timeout=settings.request_timeout_seconds,
            headers={"User-Agent": settings.user_agent},
        )

    def get_flyer(self, flyer_identifier: str) -> dict:
        if settings.lidl_fixture_dir:
            fixture_path = settings.lidl_fixture_dir / f"{flyer_identifier}.json"
            if fixture_path.exists():
                return json.loads(fixture_path.read_text(encoding="utf-8"))

        response = self.client.get(
            f"{self.base_url}/flyer",
            params={"flyer_identifier": flyer_identifier},
        )
        response.raise_for_status()
        return response.json()

    def get_flyer_fallback(self) -> dict:
        response = self.client.get(
            f"{self.base_url}/flyer-fallback",
            params={"domain_url": "https://www.lidl.pt"},
        )
        response.raise_for_status()
        return response.json()

    def get_flyer_overview_html(self) -> str:
        response = self.client.get(self.listing_page_url)
        response.raise_for_status()
        return response.text

    def get_flyer_overview_ids(self) -> list[str]:
        html = self.get_flyer_overview_html()
        ids = re.findall(r'data-track-id="([0-9a-f-]{36})"', html)
        if not ids:
            ids = re.findall(r'id="flyer-([0-9a-f-]{36})"', html)
        return list(dict.fromkeys(ids))

    def download_binary(self, url: str, output_path: Path) -> Path:
        response = self.client.get(url)
        response.raise_for_status()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)
        return output_path

    def close(self) -> None:
        self.client.close()


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value[:10])
