from datetime import date

import typer

from leaflet_automation.app.logging import configure_logging
from leaflet_automation.jobs.discover_leaflets import run_lidl_discovery
from leaflet_automation.jobs.extract_leaflet import run_lidl_extraction
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
    try:
        result = run_lidl_extraction(leaflet_id)
    except LookupError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    typer.echo(
        " | ".join(
            [
                result.leaflet.id,
                result.leaflet.program_type.value,
                f"candidate-pages={result.candidate_pages}",
                f"extracted={result.extracted_products}",
                f"persisted={result.persisted_products}",
            ]
        )
    )


@app.command("run-weekly-lidl")
def run_weekly_lidl_command() -> None:
    count = run_weekly_lidl(today=date.today())
    typer.echo(f"Discovered {count} target leaflets.")
