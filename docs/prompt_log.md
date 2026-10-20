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

## S3 bis S11 Rechenkern
Vorgehen: Vor der Umsetzung wurden alle Zellformeln der Blätter Input (Zeile 14), Touren (Zeilen 14 und 15), Routen (Zeile 14), Overview & Results (Abschnitte 1, 5, 6) und Assumptions (A bis K, insbesondere J2 Schnittstelle und K2 Formelregister) mit openpyxl ausgelesen. Die Python-Funktionen übertragen die Zellformeln in derselben Rechenreihenfolge.

S3 Modelle und Parameterlader: `models.py` (pydantic v2: `Shipment` nach Input!A:H, `Assumptions`, `Vehicle`, `Tour`, `ScenarioKpis`, `Route`, `CheckResult`; Rechenzeilen als Dataclass `ShipmentRow`), `workbook.py` (Lesen der Mappe, nie Speichern, lokaler Cache), `assumptions.py` (alle Parameter über die benannten Bereiche `p_*` und `v_*`, mit ID, Einheit, Typ, Quelle und Zelle; keine Standardwerte im Code), `excelfn.py` (Excel-Semantik: TRIM, MATCH ohne Groß-/Kleinschreibung mit Platzhaltern, ROUND kaufmännisch über Decimal, ROUNDUP und Kriterien mit 15 Stellen, Datumslogik).
S4 Geodaten und Distanz: `geo.py` (J2.1 `resolve_place`, Haversine K2.1), `distance.py` (J2.2, Priorität Eingabe, Relationstabelle, Näherung).
S5 Emissionen: `emissions.py` (K2.8, K2.9, K2.12). S6 Kosten: `costs.py` (K2.10, C04). S7 Fahrzeugwahl: `vehicle.py` (K2.3 bis K2.7, Rangregel), `validation.py` (Spalte I).
S8 Bündelung: `bundling.py` (J2.5 bis J2.7, K2.13 bis K2.16). S9 Bahn: `rail.py` (J2.4, K2.11).
S10 Szenarien: `scenarios.py` (Gesamtlauf, Kennzahlen K2.17, Cockpit-Status, Routen, Sensitivität mit Parameteränderung aus dem Text der Excel-Tabelle).
S11 Prüfungen: `checks.py` (20 Prüfungen, Gesamtstatus C162), `analysis.py` (Overview Abschnitte 3, 4, 7), `explain.py` (Formel, Parameter, Quelle, Systemgrenze, Verifikation je Kennzahl).

Ergebnisse:
- Zeilenvergleich: alle 2.266 Sendungen, alle 55 Rechenspalten I bis BK, keine Abweichung über 1e-13 (Abnahme 1e-9).
- Blatt Touren: 1.715 Zeilen und 428 Tourköpfe ohne Abweichung; 318 gebündelte Touren, 1.488 Sendungen in Sammeltouren. Blatt Routen: 45 Relationen ohne Abweichung.
- Kennzahlen Ist, M2, M3 innerhalb 1e-9; C04 = 0,646527; 551 Bahn-Sendungen; Cockpit "Plan zulässig".
- Snapshot: 14 Zeilen (Basisfall und 13 Szenarien), größte absolute Abweichung 1,6e-10 (Abnahme 1e-8). Der gespeicherte Basisfall weicht selbst um 1,5e-10 von der Live-Zeile der Excel ab (Momentaufnahme aus LibreOffice).
- 20 Prüfungen mit Soll, Ist und Status wie Excel; Gesamtstatus "Alle Prüfungen bestanden".
- T01 bis T10: Die Datensätze liegen nicht vor. Die Tests bauen Datensätze nach der Beschreibung in Assumptions K4 nach und prüfen das beschriebene Verhalten (gültige Zeilen, Meldungen, Überlauf, Parameterfälle, Next-Fit). Die Ergebniszahlen aus `testprotokoll_v11.json` sind damit nicht nachgerechnet.
- Eigenschaftstests (hypothesis): keine Tour über Nutzlast oder Paletten, jede gültige Sendung genau einer Tour, der Bahn oder dem Einzelversand mit mehreren Fahrzeugen zugeordnet, Summe der Zuordnung gleich Tourwert, Rangregel monoton.
Technischer Befund: macOS markiert die `.pth`-Datei der Editable-Installation im Ordner Desktop als versteckt; Python 3.12 überspringt sie. Lösung: `PYTHONPATH=src` im Makefile und `pythonpath` in der pytest-Konfiguration.
Gates G3, G4, G5: bestanden.
