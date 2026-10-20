# Prompt-Log

Werkzeug: Claude Code (Modell Claude Opus 5.5). Jeder Eintrag nennt Prompt, Ergebnis, Gate und Prüfung.

## Start
Prompt: Gesamtpaket lesen, Projektordner anlegen, S0 bis S18 nacheinander ausführen.
Ergebnis: Projektordner `transportkonzept-artefakt` angelegt, Excel-Dateien nach `data/excel` kopiert (schreibgeschützt, nicht versioniert), mitgelieferte Referenzdateien nach `data/reference/given`.
Entscheidungen der Gruppe: nur lokales git, kein Remote; Agent wird ohne Schlüssel mit Ersatzanbieter und Demo-Modus getestet.

## S0 GitHub-Setup
Ergebnis: `.gitignore`, `.env.example`, PR-Vorlage, `ci.yml`, `THIRD_PARTY.md`, dieses Log.
Action-Versionen geprüft am 20.10.2026 über die GitHub-API: `actions/checkout` v7.0.1, `astral-sh/setup-uv` v10.3.0.
Vorschlag Branch-Schutz für `main` (im GitHub-Interface zu setzen):
1. Require a pull request before merging, 1 approval, dismiss stale approvals.
2. Require status checks to pass: `ci / test`, branches up to date.
3. Require conversation resolution.
4. Block force pushes und Löschen von `main`.
5. Regeln auch für Administratoren.
Gate G0: ohne Remote nicht prüfbar. Ersatz: dieselben Befehle wie in `ci.yml` lokal (siehe G1).

## S1 Projektgerüst
Ergebnis: uv-Projekt (Python 3.12 gepinnt), `pyproject.toml` mit ruff, mypy (strict für `tk.*`), pytest; Makefile (run, test, lint, reference); Paket `src/tk` mit Modulen laut Abschnitt 6.
Gate G1: `ruff check`, `mypy src`, `pytest` grün.

## S2 Referenz erzeugen
Ergebnis: `scripts/make_reference.py` liest die Beispieldaten-Mappe mit openpyxl (`read_only`, `data_only=True`, ohne Speichern) und schreibt `expected.json`, `snapshot.json` (14 Zeilen: Basisfall und 13 Szenarien), `sendungen_ref.csv` (2.266 Zeilen, Spalten A bis BK), `touren_ref.csv` (1.715 Zeilen) und `routen_ref.csv` (45 Relationen). Jeder Zellbezug steht im Skript.
Prüfung: Abgleich mit Abschnitt 2.5 ohne Abweichung; Abgleich mit der mitgelieferten `referenz_v11_kennzahlen.json` mit relativer Abweichung höchstens 4,3e-14.
Befunde für die Gruppe:
- Die aktive Bahn-Traktion ist laut Blatt Assumptions (A04) "elektrisch" mit 10,8 g/tkm (B3.5). Abschnitt 2.4 des Gesamtpakets nennt "Diesel" für 10,8 g/tkm; Diesel hat laut B3.6 30,7 g/tkm. Maßgeblich ist die Excel.
- M2 ist in der Excel kein eigener Lauf ohne Bahn: Overview C11 = Plan der Sendungen ohne Bahn plus Ist der Bahn-Sendungen. Die Tourbildung läuft nur einmal auf den Lkw-Sendungen nach der Bahnprüfung. Der Port übernimmt diese Definition.
- Die Datensätze der Tests T01 bis T10 liegen nicht vor, nur ihr Protokoll (`testprotokoll_v11.json`).
- Die CSV-Referenzen enthalten Sendungsdaten und sind deshalb nicht versioniert (`.gitignore`); `expected.json` und `snapshot.json` enthalten nur Summen und sind versioniert.
Gate G2: bestanden.
