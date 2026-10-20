# Transportkonzept-Artefakt

Python-Port des Excel-Modells v11 "Nachhaltiges Transportkonzept" (Seminar Planungsprozesse BLO513/WPML733, HWG Ludwigshafen) mit Weboberfläche, Karte und Assistent. Die Excel ist maßgeblich; die Python-Rechnung trifft sie für Kennzahlen und alle 2.266 Sendungen auf 1e-9.

## Start in unter 10 Minuten

Voraussetzungen: macOS, Linux oder Windows; Internet für die Installation; die Excel-Mappe der Gruppe.

1. uv installieren (einmalig, Python 3.12 lädt uv selbst):
   - macOS und Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
2. Projektordner öffnen und Pakete installieren: `uv sync`
3. Excel-Mappen nach `data/excel/` kopieren (werden nicht versioniert):
   - `Thema1_Transportkonzept_v11_Beispieldaten.xlsx` (Pflicht)
   - `Thema1_Transportkonzept_v11.xlsx` (leere Vorlage, nur für den Round-Trip-Test)
4. Referenz erzeugen: `make reference`
5. Starten: `make run`, dann im Browser `http://127.0.0.1:8080` öffnen. Die Vorschau des Design-Systems liegt unter `/vorschau`.

Ohne `make` (etwa unter Windows) lauten die Befehle:

| Zweck | Befehl |
|---|---|
| Start | `uv run python -m tk.ui.app` mit Umgebungsvariable `PYTHONPATH=src` |
| Tests | `uv run pytest -q` |
| Prüfung | `uv run ruff check .` und `uv run mypy src` |
| Referenz | `uv run python scripts/make_reference.py` |

Hinweis macOS: Liegt das Projekt in einem synchronisierten Ordner (etwa der Schreibtisch mit iCloud), markiert macOS die `.pth`-Datei der Installation als versteckt und Python 3.12 überspringt sie. Deshalb setzt das Makefile `PYTHONPATH=src` und pytest `pythonpath = ["src", "."]`.

## Assistent (optional)

1. Schlüssel in Google AI Studio anlegen.
2. `.env.example` nach `.env` kopieren und `GEMINI_API_KEY=` ausfüllen. Der Schlüssel gehört nie in Code, Chat oder Repository.
3. Ohne Schlüssel oder bei Ratenlimit läuft der Demo-Modus mit drei aufgezeichneten Fällen. Erzwingen: `TK_DEMO_MODE=1`.

Die kostenlose Stufe darf Eingaben zur Produktverbesserung nutzen: nur synthetische Daten eingeben. Die Demo läuft lokal, nicht als öffentliche Instanz.

## Aufbau

| Ordner | Inhalt |
|---|---|
| `src/tk` | Rechenkern (kennt weder Oberfläche noch Agent): `geo`, `distance`, `vehicle`, `emissions`, `costs`, `rail`, `bundling`, `scenarios`, `checks`, `explain`, `export` |
| `src/tk/agent` | Assistent: `LLMProvider`, Werkzeuge, Orchestrator mit Zahlenprüfung, Spur, Demo-Modus |
| `src/tk/ui` | Oberfläche (NiceGUI): Seite, Karte, Design-System |
| `scripts/make_reference.py` | Referenzwerte aus der Excel (`data/reference`) |
| `tests` | Abnahme gegen die Excel, Eigenschaften, Agent, Export, Kontrast, Platzhalter |
| `docs` | `Gesamtpaket.md`, `Annahmen.md`, `Demo_Skript.md`, `prompt_log.md`, `Pruefprotokoll.md` |

## Abnahme

`make lint test` muss grün sein. Kennzahlen und Zeilen weichen höchstens 1e-9 von der Excel ab, die Sensitivität höchstens 1e-8. Tests, die die Excel brauchen, werden ohne Mappe übersprungen (CI).

## Daten und Lizenzen

Postleitzahl- und Ortsdaten: GeoNames, geonames.org, CC BY 4.0. Kartendaten: © OpenStreetMap contributors (ODbL). Weitere Komponenten: `THIRD_PARTY.md`. Das Repository ist privat; der Code steht unter der MIT-Lizenz (`LICENSE`). Daten und Excel-Mappen sind nicht enthalten.
