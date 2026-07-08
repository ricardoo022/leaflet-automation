from datetime import date

from leaflet_automation.app.config import settings
from leaflet_automation.core.enums import ProgramType
from leaflet_automation.core.models import Leaflet
from leaflet_automation.db.repositories.leaflets import LeafletRepository
from leaflet_automation.db.schema import initialize_schema
from leaflet_automation.db.sqlite import connect
from leaflet_automation.retailers.lidl.adapter import LidlAdapter


def run_lidl_discovery(
    today: date | None = None,
    allowed_program_types: set[ProgramType] | None = None,
) -> list[Leaflet]:
    current_date = today or date.today()
    adapter = LidlAdapter()
    connection = connect(settings.database_path)
    initialize_schema(connection)

    try:
        leaflets = adapter.discover_leaflets(current_date)
        target_leaflets = adapter.filter_target_leaflets(leaflets, current_date)
        if allowed_program_types is not None:
            target_leaflets = [
                leaflet for leaflet in target_leaflets if leaflet.program_type in allowed_program_types
            ]
        LeafletRepository(connection).upsert_many(target_leaflets)
        return target_leaflets
    finally:
        adapter.close()
        connection.close()
