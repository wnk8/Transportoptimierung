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

## S12 Design-System
Ergebnis: `ui/theme.py` (Farbtokens 7.2, Kartenlinien, Status-Chip, Szenario-Umschalter, CSS mit `tk-card`, `tk-label`, `tk-kpi`, Fokus-Ring, 150 ms Übergänge, Kachelfilter), `ui/format.py` (deutsches Zahlenformat mit schmalem Leerzeichen und echtem Minuszeichen), `ui/components.py` (Kennzahlenkachel, Zustände leer, lädt, Fehler, Erfolg, Hinweis), `ui/preview.py` (Seite `/vorschau`), Schrift Inter 4.1 lokal (Regular, Medium, SemiBold; Lizenz SIL OFL 1.1 beigelegt; Quelle: GitHub-Release rsms/inter v4.1).
Prüfung: `tests/test_contrast.py` rechnet alle Text-Hintergrund-Paare (mindestens 4,5 : 1), alle Status-Chips und die Kartenlinien gegen eine entsättigte Kachelfläche `#E5E5E5` und gegen Weiß (mindestens 3 : 1). Die in 7.2 genannten Kontrastwerte sind nachgerechnet und stimmen. `tests/test_no_placeholders.py` sucht die vier in Gesamtpaket 7.6 genannten Platzhalterwörter; das Wort für Musterdaten zählt nur alleinstehend, damit der Dateiname der Excel ("Beispieldaten") erlaubt bleibt.
Gate G6 (Teil): bestanden.

## S13 Eingabe, Kennzahlen, Tabellen
Ergebnis: `ui/app.py` nach Layout 7.4: Kopfzeile mit Szenario-Umschalter und Status-Chip (Abbild von Input!R8), Eingabepanel (Formular mit Ortszuordnung beim Verlassen des Feldes, Einfügen aus Excel, CSV- und XLSX-Upload, Freitext), Parameterpanel (A01, A02, A05, A08, A10, A09, I01, A04 mit C01; Standardwerte und Namen aus Assumptions; Zurücksetzen; Sofortberechnung im Hintergrund-Thread), vier Kennzahlenkacheln mit Delta und "Wie berechnet?", Tabs Sendungen (Filter Verkehrsträger und Tour), Touren, Szenarien (Tabelle, ein gruppiertes Balkendiagramm, Sensitivität mit Nachrechnung), Erklärung, Prüfungen (mit Referenzabgleich gegen Excel), Agent-Spur; Fußzeile mit Attributionen und Datenstand. `inputs.py` übernimmt Zahlen in Textform wie beim Einfügen in Excel (Dezimalkomma und Tausenderpunkt).
Beim Start sind die Beispieldaten der Excel geladen. Fehlt die Mappe, zeigt die Seite Ursache und nächsten Schritt.
Prüfung im Browser (Playwright): Kennzahlen M3 −53,3 %, −24,9 %, −67,7 %, Servicegrad 75,7 %, Status "Plan zulässig". Parameteränderung A01 = 400 ergibt sofort 945 Bahn-Sendungen, −67,8 % CO₂e, −16,1 % Kosten, −78,4 % Lkw-km, wie Zeile "Bahn-Mindestdistanz 400 km" der Sensitivitätstabelle.
Korrektur während der Prüfung: Einheiten und Typ der Fahrzeugkennwerte (C2) wurden in der Erklärung falsch zugeordnet; jetzt aus den Spaltenköpfen der Fahrzeugtabelle.

## S14 Karte
Spike (vor der Umsetzung, Testseite außerhalb des Repos): `ui.leaflet` mit Polylinie (`generic_layer`), Linienstärke, Strichmuster (`dashArray`), Popup und synchronem Zoom zweier Karten. Ergebnis: alles möglich. Einschränkung: `bindPopup` wirkt erst, wenn die Ebene im Browser existiert (nach `initialized()`). Kein Rückfall auf FastAPI nötig.
Ergebnis: `ui/map_view.py` mit zwei Karten (Vorher Ist, Nachher gewähltes Szenario), Luftlinien aus Blatt Routen, Kodierung Farbe plus Linienstärke plus Muster (Bahn gestrichelt und seitlich versetzt), Popup je Relation, Legende mit "Luftlinie, schematisch", OSM-Attribution, Kachelfilter. Rückfall: Knoten-Kanten-Ansicht als SVG, automatisch, wenn eine Kachel desselben Servers nicht innerhalb von 10 s lädt, und jederzeit umschaltbar.
Befunde aus der Browserprüfung: (1) Leaflet misst den Container beim Anlegen; im Flex-Layout war die Kartenebene versetzt. Lösung: nach der Initialisierung `invalidateSize` und `setView`. (2) Gegenseitiger Zoomabgleich erzeugte ein Echo; Abgleich nur bei Abweichung. (3) Kacheln laden im Testbrowser teils langsam; die Prüfzeit der Kachelprobe wurde von 4 s auf 10 s erhöht.
Gate G6: UI, Karte, Kontrasttest und Platzhaltertest bestanden.

## S15 Agent
Dokumentation geprüft am 20.10.2026: google-genai 2.31 (installiert), Doku v2.30 über Context7: manuelle Funktionsaufrufe mit `FunctionDeclaration(parameters_json_schema=...)`, `AutomaticFunctionCallingConfig(disable=True)`, Rückgabe über `Part.from_function_response`. Modellname über `GEMINI_MODEL`, sonst Alias `gemini-flash-latest`. Die Limits der kostenlosen Stufe sind in keiner offiziellen, aktuellen Tabelle auffindbar (Websuche: Flash-Modelle etwa 15 Anfragen je Minute; Pro laut Drittquelle seit 2026 nicht mehr kostenlos, nicht bestätigt). Vor der Demo in Google AI Studio prüfen.
Ergebnis: `agent/provider.py` (Schnittstelle `LLMProvider`, `GeminiProvider`, `ScriptedProvider`), `agent/tools.py` (parse_shipments, validate_shipments, plan_scenarios, get_route_summary, compare_scenarios, explain_result), `agent/orchestrator.py` (manuelle Schleife, höchstens 8 Schritte, Zahlenprüfung per Regex gegen Werkzeugausgaben und Anfrage, Wiederholung mit 2, 4, 8 s Wartezeit bei HTTP 429, danach Demo-Modus), `agent/trace.py`, `ui/agent_panel.py` (Freitext, Übernahme in die Eingabe, Agent-Spur).
Schlüssel nur aus `GEMINI_API_KEY` (lokal `.env`, von git ausgeschlossen).
Tests mit Ersatzanbieter: Zahlenprüfung, unbekannter Ort, Gewicht 0, fehlende Pflichtfelder, Aufforderung zum Schätzen (Antwort verworfen), Aufforderung den Kern zu umgehen (Antwort verworfen), Ratenlimit mit Wiederholung und Wechsel in den Demo-Modus, Protokoll jedes Aufrufs.
Nicht geprüft: ein Lauf mit dem echten Gemini-Modell (kein Schlüssel vorhanden). Das bleibt ein manueller Schritt der Gruppe; der Code-Pfad `GeminiProvider` ist ungetestet.
Gate G7 (Teil): bestanden mit dieser Einschränkung.

## S16 Export und Demo-Modus
Ergebnis: `export.py` (CSV mit Semikolon und Dezimalkomma, XLSX mit Blatt "Sendungen", jeweils nur Spalten A bis H; `write_into_template` schreibt in eine Kopie der Vorlage nach Input!A14:H, das Original bleibt unverändert), `ui/export_panel.py`, `agent/demo.py` (drei aufgezeichnete Fälle: Einzelsendung, Bündelung, Bahnfall; Zahlen werden aus den Werkzeugausgaben eingesetzt; andere Anfragen werden im Demo-Modus nicht beantwortet), `docs/Demo_Skript.md`.
Prüfung: Round Trip CSV und XLSX (Export, Import, Neuberechnung) ergibt identische Kennzahlen; Schreiben in eine Testkopie der Excel-Vorlage mit identischen Eingabezellen und unverändertem Original.
Befund: Der XLSX-Export hieß zuerst "Input" und wurde beim Wiedereinlesen wie die Modellmappe ab Zeile 14 gelesen; jetzt Blatt "Sendungen", die Modellmappe wird am Blatt "Assumptions" erkannt.
Nicht automatisierbar: Neuberechnung der Testkopie in Microsoft Excel (openpyxl rechnet keine Formeln). Manueller Schritt: Kopie in Excel öffnen, neu berechnen, Overview C10:L12 mit der App vergleichen.
Gate G7: bestanden mit den genannten Einschränkungen (kein Live-Gemini, Excel-Neuberechnung manuell).

## S17 Dokumentation und Prompt-Log
Ergebnis: `README.md` (Start in fünf Schritten, Befehle ohne make, Assistent, Aufbau, Abnahme, Lizenzen), `docs/Annahmen.md` (alle Parameter mit Wert, Einheit, Beleg und Quelle aus Assumptions; Formeln in LaTeX; Systemgrenze; Verifikationsstatus; unsichere Quellen als **unbelegt** oder **Sekundärquelle** markiert), `THIRD_PARTY.md` final, dieses Log.

## Übersicht der Werkzeuge
| Werkzeug | Einsatz |
|---|---|
| Claude Code (Claude Opus 5.5) | Lesen des Gesamtpakets und der Excel-Formeln, Umsetzung S0 bis S17, Tests, Browserprüfung (Playwright), Review S18 |
| Context7, Websuche | Prüfung der Gemini-Dokumentation und der Limits der kostenlosen Stufe |
| GitHub-API (`gh`) | aktuelle Versionen der GitHub Actions und der Schrift Inter |
| Excel v11 | fachliche Referenz; gespeicherte Werte über openpyxl |

## Prüfung durch die Gruppe (offen)
Die folgenden Punkte sind nicht durch Claude Code erledigbar und gehören zur Abnahme durch die Gruppe:
1. Code-Review jedes Merges durch ein anderes Gruppenmitglied (lokal ohne Pull Request gemergt, weil kein Remote vereinbart war).
2. Excel-Mappe in Microsoft Excel neu berechnen und `make reference` wiederholen (die gespeicherten Werte stammen aus LibreOffice).
3. Ein Lauf des Assistenten mit echtem Gemini-Schlüssel, inklusive der Negativfälle aus Abschnitt 10.
4. Belege für die als **unbelegt** markierten Parameter (P4, P5).
5. Freigabe der Seminardaten, bevor die Excel in ein Remote-Repository kommt.

## Kritische Reflexion der KI-Nutzung
- Nutzen: Der Port der rund 60 Rechenspalten, der Tourbildung und der 20 Prüfungen entstand in einer Sitzung. Der Abgleich gegen alle Zellen der Excel (statt nur gegen Summen) hat gezeigt, dass die Übertragung bis 1e-13 genau ist. Ohne diesen Abgleich wäre Vertrauen in die KI-Ausgabe nicht begründbar.
- Grenzen der Kontrolle: Die Genauigkeit belegt nur, dass Python dieselbe Rechnung wie die Excel ausführt. Sie belegt nicht, dass die Excel fachlich richtig ist. Fachliche Annahmen (A01, A05, A10, I01, Verbrauchswerte, Dieselfaktor) bleiben Setzungen der Gruppe; die KI hat sie nicht geprüft und nicht verbessert.
- Fehler der KI, die erst durch Prüfung sichtbar wurden: falsche Zuordnung von Einheit und Typ der Fahrzeugkennwerte in der Erklärung; XLSX-Export, der beim Wiedereinlesen falsch erkannt wurde; Testdatensatz mit Start gleich Ziel; ein Demo-Modus, der zunächst bei freien Anfragen einen fremden aufgezeichneten Fall abgespielt hätte. Alle wurden durch Tests oder Browserprüfung gefunden und behoben.
- Tests der KI über eigene Arbeit: Die Tests T01 bis T10 sind Nachbauten nach Beschreibung, nicht die Originaldatensätze. Die Agent-Tests prüfen den Orchestrator mit einem Ersatzanbieter, nicht das Sprachmodell. Diese Grenzen stehen in den Testdateien.
- Sprachmodell im Produkt: Der Assistent rechnet nicht. Die Zahlenprüfung verwirft jede Antwort mit Zahlen ohne Werkzeugquelle. Sie erkennt keine falsch zitierten Texte und keine sinnentstellende Auswahl von Zahlen; die Agent-Spur bleibt deshalb sichtbar.
- Datenschutz: Die kostenlose Gemini-Stufe darf Eingaben verwenden. Nur synthetische Daten eingeben; die Demo läuft lokal.

## S18 Unabhängiger Review
Ergebnis: `docs/Pruefprotokoll.md`. Alle Rechen-Gates bestanden; G0 ohne Remote nur lokal simuliert; Befunde B1 bis B7.
Danach getrennt vom Review behoben: B1 (Ordner `data/excel` im Klon) und B2 (einspaltiges Layout unter 1.280 px). Offen für die Gruppe: B4 (Gemini live), B5 (Neuberechnung in Microsoft Excel), Review durch ein Gruppenmitglied, Remote-Repository mit Schutzregeln.

## Push auf GitHub (Nachtrag)
Remote: `github.com/wnk8/Transportoptimierung` (privat). Der vorhandene Initial-Commit mit MIT-Lizenz wurde zusammengeführt, nicht überschrieben; README nennt die Lizenz.
Befund: `astral-sh/setup-uv` hat keinen Major-Tag `v10`, der erste CI-Lauf schlug deshalb fehl. Jetzt `v10.3.0` fest. Danach CI grün (ruff, mypy, pytest ohne Excel-Daten).
Gate G0: CI grün. Branch-Schutz für `main` setzt die Gruppe im GitHub-Interface (Vorschlag unter S0).

## Karte ausbauen (R1 bis R6)
Auftrag: Straßenrouten im Vergleich zur Luftlinie, Vergleich der Routenaufteilung, Begründung der Fahrzeugwahl, Klick auf eine Route mit Ist gegen Plan. Entscheidungen der Gruppe: OpenRouteService mit Profil driving-hgv; Straßen-km werden angezeigt und können optional über die Relationstabelle gerechnet werden.

R1 Spike: Ein Klick auf eine Polylinie lässt sich über `layer.run_method(':on', "'click'", "() => emitEvent(...)")` an Python melden (die NiceGUI-Komponente wertet Argumente mit Präfix `:` als JavaScript aus). Kein Rückfall über `map-click` nötig.
R2 Routing: `src/tk/routing.py` (ORS-Client mit 1,6 s Abstand und Wiederholung bei 429, Cache `data/routes/routes.json`, Linienvereinfachung, Reihenfolge der Tourstopps "nächster Nachbar" nur zur Darstellung), `scripts/make_routes.py`, `make routes`. Limits laut openrouteservice.org: 2.000 Directions je Tag, 40 je Minute. Kein Schlüssel vorhanden: getestet mit nachgebauten ORS-Antworten (httpx.MockTransport), noch kein Live-Abruf.
R3 Vergleich: `src/tk/compare.py` (Fahrzeugalternativen je Ladung, Tourvergleich mit den vier Bedingungen, Relation Ist gegen Plan, Straße gegen Luftlinie). Prüfung: die gewählte Alternative entspricht für alle 2.266 Sendungen und 428 Touren der Excel; die Summen je Relation ergeben die Kennzahlen Ist, M2 und M3.
R4 Variante: `with_road_km` ergänzt die Relationstabelle um Straßen-km; Quelle wird "Relationstabelle" wie in der Excel; Export für PLZ_Orte R:T. Die Standardrechnung bleibt unverändert.
