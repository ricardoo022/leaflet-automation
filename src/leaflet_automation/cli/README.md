# `cli`

## Purpose

This package exposes the operator-facing command line interface using Typer.

It is the top-level execution surface for the repository.

## What Currently Works

- logging is configured through the app callback
- `discover-lidl` runs the implemented Lidl discovery flow
- `run-weekly-lidl` runs the current weekly wrapper and prints a count
- command output is printed in plain text for operator use

## Important Files

- `main.py`
  - creates the Typer application
  - defines all current commands
  - maps CLI actions to jobs in `src/leaflet_automation/jobs/`

## Commands

- `leaflets discover-lidl`
  - discovers Lidl leaflets
  - persists selected leaflets
  - prints one line per discovered target leaflet

- `leaflets extract-lidl <leaflet-id>`
  - currently a placeholder
  - does not execute real extraction logic yet

- `leaflets run-weekly-lidl`
  - runs the weekly wrapper job
  - currently returns the count of selected leaflets from the discovery path

## How It Fits Into The Flow

The CLI is the entrypoint for all current runnable behavior:

1. configure logging
2. call a job
3. let the job coordinate adapters and persistence
4. print a human-readable result

## Maintainer Notes

- `extract-lidl` exists in the interface before the backend flow exists.
- `run-weekly-lidl` currently behaves more like "run current Lidl discovery" than a strict weekly-only workflow.
- There are no command flags yet for output format, date overrides, debugging, or retailer selection.
- Error handling is currently minimal and mostly left to exceptions from deeper layers.
