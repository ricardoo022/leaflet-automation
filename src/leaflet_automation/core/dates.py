from datetime import date

from leaflet_automation.core.models import Leaflet


def is_upcoming_or_current(leaflet: Leaflet, today: date) -> bool:
    if leaflet.offer_end_date and leaflet.offer_end_date < today:
        return False
    if leaflet.offer_start_date:
        return leaflet.offer_start_date >= today or (
            leaflet.offer_end_date is not None and leaflet.offer_end_date >= today
        )
    if leaflet.start_date:
        return leaflet.start_date >= today or (
            leaflet.end_date is not None and leaflet.end_date >= today
        )
    return False
