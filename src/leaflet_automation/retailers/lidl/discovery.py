import logging

from leaflet_automation.app.config import settings
from leaflet_automation.core.dedupe import dedupe_leaflets
from leaflet_automation.core.models import Leaflet
from leaflet_automation.retailers.lidl.api import LidlLeafletApi
from leaflet_automation.retailers.lidl.parser import parse_leaflet


logger = logging.getLogger(__name__)


# Seed IDs verified during research. Replace or expand this with dynamic discovery.
SEED_FLYER_IDS = [
    "019e6f22-4ece-7cf2-8ab3-6a958456e86a",
    "019e6f27-3178-7eb7-a151-758e09e1eb07",
    "019e4a4b-a039-7ba5-87b0-bca69e18d380",
]


def discover_leaflets(api: LidlLeafletApi) -> list[Leaflet]:
    discovered: list[Leaflet] = []
    pending = _initial_flyer_ids(api)
    seen: set[str] = set()

    while pending:
        flyer_id = pending.pop(0)
        if flyer_id in seen:
            continue
        seen.add(flyer_id)

        payload = api.get_flyer(flyer_id)
        leaflet = parse_leaflet(payload)
        discovered.append(leaflet)

        for related in payload["flyer"].get("relatedFlyers", []):
            related_id = related.get("id")
            if related_id and related_id not in seen:
                pending.append(related_id)

    return dedupe_leaflets(discovered)


def _initial_flyer_ids(api: LidlLeafletApi) -> list[str]:
    if settings.lidl_fixture_dir:
        return list(SEED_FLYER_IDS)

    try:
        discovered_ids = api.get_flyer_overview_ids()
    except Exception as error:
        logger.warning(
            "Falling back to hardcoded Lidl seed flyer IDs because overview discovery failed: %s",
            error,
        )
        discovered_ids = []

    if not discovered_ids:
        logger.warning("No flyer IDs were discovered on the Lidl overview page; using hardcoded fallback seeds.")

    return list(dict.fromkeys([*discovered_ids, *SEED_FLYER_IDS]))
