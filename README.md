# Leaflet Automation

Python backend scaffold for discovering retailer leaflets, filtering relevant campaigns, and extracting products for downstream automation.

Current scope:

- API-first leaflet discovery for Lidl
- backend-only pipeline
- retailer adapter architecture for future expansion

Main CLI entrypoint:

- `leaflets discover-lidl`
- `leaflets extract-lidl <leaflet-id>`
- `leaflets run-weekly-lidl`
