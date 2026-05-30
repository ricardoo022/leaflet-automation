from datetime import date

from leaflet_automation.core.dates import is_upcoming_or_current
from leaflet_automation.core.enums import ProgramType
from leaflet_automation.core.models import Leaflet, LeafletPage
from leaflet_automation.retailers.lidl.keywords import CATEGORY_KEYWORDS


def infer_program_type(leaflet: Leaflet) -> ProgramType:
    name = f"{leaflet.name} {leaflet.title} {leaflet.subcategory or ''}".lower()
    if "fim de semana" in name or "sexta" in name:
        return ProgramType.WEEKEND
    if "seman" in name or leaflet.subcategory == "Semanais":
        return ProgramType.WEEKLY
    if "especial" in name:
        return ProgramType.SPECIAL
    return ProgramType.UNKNOWN


def filter_target_leaflets(leaflets: list[Leaflet], today: date) -> list[Leaflet]:
    selected: list[Leaflet] = []
    for leaflet in leaflets:
        leaflet.program_type = infer_program_type(leaflet)
        if is_upcoming_or_current(leaflet, today):
            selected.append(leaflet)
    return selected


def is_candidate_page(page: LeafletPage) -> bool:
    text = f"{page.alt_text or ''} {page.keywords or ''}".lower()
    return any(keyword in text for keywords in CATEGORY_KEYWORDS.values() for keyword in keywords)
