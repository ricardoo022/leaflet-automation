from datetime import date

import httpx

from leaflet_automation.app.config import settings


class LidlLeafletApi:
    base_url = "https://endpoints.leaflets.schwarz/v4"

    def __init__(self) -> None:
        self.client = httpx.Client(
            timeout=settings.request_timeout_seconds,
            headers={"User-Agent": settings.user_agent},
        )

    def get_flyer(self, flyer_identifier: str) -> dict:
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

    def close(self) -> None:
        self.client.close()


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value[:10])
