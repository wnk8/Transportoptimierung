# Drittkomponenten und Datenquellen

Stand: 20.10.2026. Lizenzen vor Abgabe verifizieren.

## Software

| Zweck | Komponente | Lizenz |
|---|---|---|
| Sprache, Paketmanager | Python 3.12, uv | PSF, MIT/Apache-2.0 |
| Modelle, Validierung | pydantic v2 | MIT |
| Daten | pandas, numpy, openpyxl | BSD-3-Clause, BSD-3-Clause, MIT |
| Oberfläche | NiceGUI (Quasar, Tailwind-Klassen) | MIT |
| Karte | Leaflet über `ui.leaflet` | BSD-2-Clause |
| Tests | pytest, hypothesis | MIT, MPL-2.0 |
| Qualität | ruff, mypy | MIT |
| Agent | Gemini API (kostenlose Stufe) hinter `LLMProvider` | Nutzungsbedingungen Google |
| Schrift | Inter, lokal eingebunden | SIL Open Font License 1.1 |
| Versionskontrolle, CI | GitHub, GitHub Actions | Nutzungsbedingungen GitHub |

## Daten und Kartendienste

| Quelle | Verwendung | Pflicht |
|---|---|---|
| GeoNames über `zauberware/postal-codes-json-xml-csv` (CC BY 4.0) | Blatt `PLZ_Orte` | Namensnennung: "Postleitzahl- und Ortsdaten: GeoNames, geonames.org, CC BY 4.0" |
| OpenStreetMap-Standardkacheln (Daten ODbL) | Hintergrundkarte | Attribution "© OpenStreetMap contributors" sichtbar; Nutzungsrichtlinie der Kachelserver beachten |

Nicht verwendet: Nominatim, OpenRouteService, OSRM.
