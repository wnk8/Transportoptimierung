# Prüfprotokoll S18 (unabhängiger Review ohne Codeänderung)

Datum: 20.10.2026. Geprüfter Stand: `main` bei Commit `5bd05cb`. Prüfer: Claude Code (Claude Opus 5.5) in einer Review-Rolle. Ein Review durch ein Gruppenmitglied ersetzt dieses Protokoll nicht.

## Ergebnis je Gate

| Gate | Kriterium | Ergebnis | Nachweis |
|---|---|---|---|
| G0 | Repo, Schutzregeln, CI grün | **nicht vollständig prüfbar** | Kein Remote vereinbart. `ci.yml` vorhanden (Actions-Versionen geprüft). Die CI-Befehle laufen in einem frischen Klon ohne Excel grün: ruff, mypy, pytest (62 bestanden, 69 übersprungen). Schutzregeln als Vorschlag im Prompt-Log |
| G1 | Toolchain grün | bestanden | `make lint`, `make test` |
| G2 | Referenz entspricht Abschnitt 2.5 | bestanden | `make reference`: "Abgleich mit Gesamtpaket 2.5: OK"; gegen mitgelieferte Referenz höchstens 4,3e-14 |
| G3 | Einzelmodule ≤ 1e-9 | bestanden | 2.266 Zeilen × 55 Spalten ohne Abweichung |
| G4 | 428 Touren, 318 gebündelt, 551 Bahnsendungen | bestanden | `test_tour_counts`; Blatt Touren und Routen zeilengleich |
| G5 | Kennzahlen, Snapshot ≤ 1e-8, 20 Checks, "Plan zulässig" | bestanden | Kennzahlen höchstens 4,1e-14 relativ; Snapshot höchstens 1,6e-10; 20 Prüfungen wie Excel |
| G6 | UI, Karte, Kontrasttest, keine Platzhalter | **bestanden mit Befund B2** | Browserprüfung bei 1440 px; Kontrast- und Platzhaltertest grün |
| G7 | Agent nur mit Werkzeugzahlen, Export-Round-Trip | **bestanden mit Einschränkung** | Negativtests mit Ersatzanbieter grün; Round Trip CSV, XLSX und Testkopie grün; kein Lauf mit echtem Gemini; Excel-Neuberechnung der Testkopie manuell offen |
| G8 | Doku, Prompt-Log, Review | **bestanden mit Befund B1** | README, Annahmen, THIRD_PARTY, Prompt-Log mit Reflexion |

## Einzelprüfungen

| Prüfung | Ergebnis |
|---|---|
| Abweichung zu `expected.json` | 4,1e-14 relativ (Abnahme 1e-9) |
| Snapshot | 1,6e-10 absolut (Abnahme 1e-8) |
| Zeilenvergleich | 0 Abweichungen über 1e-9 (auch über 1e-13) |
| Round Trip | Export CSV und XLSX, Import, Neuberechnung: Kennzahlen identisch; Eingabezellen der Vorlagenkopie identisch, Original unverändert |
| Kontrast | alle Paare aus 7.2 bestanden, dokumentierte Werte nachgerechnet |
| Platzhalter | keine Treffer |
| Agent-Negativtests | unbekannter Ort, Gewicht 0, fehlende Pflichtfelder, Schätzaufforderung, Umgehung des Kerns, Ratenlimit: bestanden (Ersatzanbieter) |
| README auf frischem Rechner | Klon, `uv sync`, `make reference`, `make test` in 25 s (ohne Download von Python und Paketen aus dem Cache); **Befund B1** |
| Attributionen | OSM in jeder Karte und in der Fußzeile; GeoNames in der Fußzeile; THIRD_PARTY vollständig |
| Secrets im Verlauf | `git log -p --all` ohne Treffer für Gemini-, GitHub- oder private Schlüssel; keine `.env`, `.xlsx`, `.csv` oder Cache-Datei versioniert |
| Stilregeln | keine Gedankenstriche und Auslassungspunkte in eigenen Texten |

## Befunde

| Nr. | Befund | Schwere | Empfehlung |
|---|---|---|---|
| B1 | Im frischen Klon fehlt der Ordner `data/excel`; Schritt 3 des README setzt ihn voraus | gering | Ordner mit `.gitkeep` versionieren oder README ergänzen |
| B2 | Unter 1.280 px Breite (einspaltig) schrumpfen die Karten auf 152 und 74 px Breite. Abschnitt 7.4 verlangt Mindestbreite 1.024 px | mittel | In der Media-Query alle Kinder von `.tk-two-col` auf volle Breite setzen |
| B3 | Commit `a86d141` (S13/S14) importiert Module, die erst in S15/S16 entstehen; dieser Zwischenstand ist allein nicht startbar | gering | Für die Abgabe zählt `main`; bei künftigen Schritten Abhängigkeiten im selben Commit |
| B4 | Kein Lauf mit echtem Gemini-Modell; `GeminiProvider` ist ungetestet | mittel | Vor der Zwischen- bzw. Abschlusspräsentation mit eigenem Schlüssel testen |
| B5 | Gespeicherte Excel-Werte stammen aus LibreOffice | mittel | In Microsoft Excel neu berechnen, `make reference`, Tests erneut |
| B6 | T01 bis T10 sind Nachbauten nach Beschreibung; die Originaldatensätze fehlen | gering | Datensätze der Gruppe beilegen, dann gegen `testprotokoll_v11.json` prüfen |
| B7 | Gesamtpaket 2.4 nennt 10,8 g/tkm als Diesel; laut Assumptions ist das der elektrische Wert | gering (Dokument) | Gesamtpaket korrigieren |

## Gesamturteil

Rechenkern und Abnahme gegen die Excel: bestanden. Oberfläche, Agent und Export: funktionsfähig, mit den Befunden B1 bis B4. Offene manuelle Schritte der Gruppe: B4, B5, Review durch ein Gruppenmitglied, Remote-Repository mit Schutzregeln.
