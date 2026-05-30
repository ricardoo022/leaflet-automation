from datetime import date

import typer

from leaflet_automation.app.logging import configure_logging
from leaflet_automation.jobs.discover_leaflets import run_lidl_discovery
from leaflet_automation.jobs.run_weekly import run_weekly_lidl

app = typer.Typer(help="Leaflet automation CLI")


@app.callback()
def main() -> None:
    configure_logging()


@app.command("discover-lidl")
def discover_lidl() -> None:
    leaflets = run_lidl_discovery(today=date.today())
    for leaflet in leaflets:
        typer.echo(
            f"{leaflet.id} | {leaflet.program_type.value} | {leaflet.name} | {leaflet.title} | {leaflet.url}"
        )


@app.command("extract-lidl")
def extract_lidl(leaflet_id: str) -> None:
    typer.echo(
        "Extraction pipeline scaffold created. "
        f"Implement lookup and extraction for leaflet {leaflet_id}."
    )


@app.command("run-weekly-lidl")
def run_weekly_lidl_command() -> None:
    count = run_weekly_lidl(today=date.today())
    typer.echo(f"Discovered {count} target leaflets.")
