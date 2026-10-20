# Drittkomponenten und Datenquellen

Stand: 20.10.2026 (Versionen aus `uv.lock`). Lizenzangaben nach Projektseiten; vor Abgabe gegen die jeweilige Lizenzdatei verifizieren.

## Software (Laufzeit)

| Zweck | Komponente | Version | Lizenz |
|---|---|---|---|
| Sprache, Paketmanager | Python, uv | 3.12, 0.11 | PSF, MIT/Apache-2.0 |
| Modelle, Validierung | pydantic | 2.14 | MIT |
| Daten | pandas, numpy, openpyxl | 3.0, 2.5, 3.1 | BSD-3-Clause, BSD-3-Clause, MIT |
| Oberfläche | NiceGUI (enthält Vue, Quasar, Tailwind) | 3.18 | MIT |
| Karte | Leaflet (über `ui.leaflet` in NiceGUI) | mit NiceGUI | BSD-2-Clause |
| Diagramm | Apache ECharts (über `ui.echart` in NiceGUI) | mit NiceGUI | Apache-2.0 |
| Formeln | latex2mathml | 3.81 | MIT |
| Agent | google-genai (Gemini API, kostenlose Stufe) | 2.31 | Apache-2.0; Nutzung der API nach Nutzungsbedingungen Google |
| Konfiguration | python-dotenv | 1.2 | BSD-3-Clause |
| HTTP | httpx | 0.28 | BSD-3-Clause |
| Schrift | Inter 4.1 (Regular, Medium, SemiBold), lokal in `src/tk/assets/fonts` | 4.1 | SIL Open Font License 1.1 (Lizenztext beigelegt) |

## Software (Entwicklung)

| Zweck | Komponente | Lizenz |
|---|---|---|
| Tests | pytest, hypothesis | MIT, MPL-2.0 |
| Qualität | ruff, mypy, pandas-stubs | MIT, MIT, BSD-3-Clause |
| Versionskontrolle, CI | git, GitHub, GitHub Actions (`actions/checkout` v7, `astral-sh/setup-uv` v10.3.0, ohne Major-Tag) | GPL-2.0 (git), Nutzungsbedingungen GitHub, MIT |
| Entwicklungswerkzeug | Claude Code (Anthropic) | Nutzungsbedingungen Anthropic |

## Daten und Kartendienste

| Quelle | Verwendung | Pflicht |
|---|---|---|
| GeoNames über `zauberware/postal-codes-json-xml-csv`, Commit b4be5a6 vom 31.07.2026 (CC BY 4.0) | Blatt `PLZ_Orte`, Ortsauflösung und Koordinaten | Namensnennung in UI-Fußzeile und Arbeit: "Postleitzahl- und Ortsdaten: GeoNames, geonames.org, CC BY 4.0"; Bearbeitung (Regeln R1 bis R5, Assumptions I1.4) ist ein Änderungshinweis |
| OpenStreetMap-Standardkacheln über `tile.osm.org` (Daten ODbL) | Hintergrundkarte | Attribution "© OpenStreetMap contributors" in der Karte und in der Fußzeile; Nutzungsrichtlinie der Kachelserver: kein Dauerbetrieb, kein Vorabladen, nur lokale Demo |
| GLEC Framework v3.2 (Smart Freight Centre), über Sekundärquelle | Emissionsintensitäten in Assumptions B3 | Quelle nennen; Primärverifikation ausstehend |
| Seminardaten (Original_Data, synthetisch und anonymisiert laut Projektplan) | Beispieldaten | Weitergabe nur nach Freigabe; nicht im Repository |

| OpenRouteService (HeiGIT), Profil driving-hgv, Standard-Plan (laut Anbieter 2.000 Directions je Tag, 40 je Minute) | Straßenrouten zur Darstellung und Variante "Straßen-km"; einmal abgerufen, lokal in `data/routes/routes.json` (nicht versioniert) | Attribution "© openrouteservice.org by HeiGIT, Daten © OpenStreetMap contributors (ODbL)" in der Ansicht; Nutzungsbedingungen von ORS; Schlüssel nur in `.env` |

Nicht verwendet: Nominatim, OSRM, OpenFreeMap, PMTiles.
