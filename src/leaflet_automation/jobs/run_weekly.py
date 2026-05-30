from datetime import date

from leaflet_automation.jobs.discover_leaflets import run_lidl_discovery


def run_weekly_lidl(today: date | None = None) -> int:
    leaflets = run_lidl_discovery(today=today)
    return len(leaflets)
