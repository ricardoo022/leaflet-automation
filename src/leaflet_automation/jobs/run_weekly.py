from datetime import date

from leaflet_automation.core.enums import ProgramType
from leaflet_automation.jobs.discover_leaflets import run_lidl_discovery


def run_weekly_lidl(today: date | None = None) -> int:
    leaflets = run_lidl_discovery(today=today, allowed_program_types={ProgramType.WEEKLY})
    return len(leaflets)
