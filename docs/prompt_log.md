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
