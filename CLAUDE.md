# Projekt: Transportplanungs-Artefakt (Seminar BLO513/WPML733)

## Auftrag
Python-Port des Excel-Modells v11 mit heller, ruhiger Oberfläche. Excel ist maßgeblich.
Abweichungen von der Excel sind Fehler, bis das Gegenteil belegt ist.

## Arbeitsweise
- Vor jedem mehrschrittigen Auftrag zuerst den Plan zeigen, dann ausführen.
- Nichts löschen ohne ausdrückliche Bestätigung. Excel-Original nie überschreiben.
- API-Schlüssel nie in Chat, Code oder Repository. Nur .env.
- Jeder Schritt endet mit Gate-Prüfung und Eintrag in docs/prompt_log.md.

## Sprache und Stil
- UI und Doku: Deutsch. Code, Bezeichner, Kommentare, Commit-Texte: Englisch.
- Keine Gedankenstriche, keine Auslassungspunkte, keine Floskeln in Texten.
- Formeln in Dokus als LaTeX.

## Fachregeln
- Keine hartkodierten Parameter. Alles aus Assumptions (A01..A14, B, C, I).
- Das Sprachmodell rechnet nie. Rechnung nur in src/tk.
- Jede Berechnung weist Formel, Annahmen, Datenquelle und Systemgrenze aus.
- Emissionsfaktoren nur mit Quelle (GLEC Framework, ISO 14083, DIN EN 16258).
- Kosten und Servicegrad immer mit ausgeben, nicht nur Emissionen.
- Fehlende Daten als "nicht berechenbar, weil [Grund]" zeigen, nie schätzen.
- Rundung vor Ranking: 6 Nachkommastellen, half away from zero (Decimal).

## Definitionen v11
- Szenarien: Ist (Einzelversand), M2 (Next-Fit je Tag und Startort), M3 (Bahnprüfung, dann M2).
- Distanz: Eingabe > Relationstabelle > Haversine * I01.
- Hauptrechnung CO2e: Fzg-km * kg/km * Auslastungsfaktor. Kontrolle: tkm * g/tkm.
- Servicegrad = 1 - Bahnanteil.

## Referenzwerte (N=2266)
Ist 306.924,11 kg | M2 -16,89 % | M3 -53,31 % | Kosten -24,95 % | Fzg-km M3 -67,69 %
551 Bahnsendungen | Servicegrad M3 75,68 % | 428 Touren, 318 gebündelt

## Design (heller Modus)
Tokens und Regeln: docs/Gesamtpaket.md Abschnitt 7. Weiße Minimal-Website (siiimple.com, white):
reines Weiß, Geist plus ein kursives Wort in Instrument Serif (beide lokal), Haarlinien statt Karten,
Pastell nur als Punkte und Pillen. Drei Seiten: Rechnen (/), Ergebnis (/ergebnis), Info (/info).
Dezente funktionale Animationen, prefers-reduced-motion schaltet sie ab. Keine Verläufe, keine
Platzhaltertexte, Farbe nie als einzige Information, Textkontrast mindestens 4,5 : 1.
Kartenlinien: Luftlinie, schematisch. Attribution OSM und GeoNames immer sichtbar.

## Abnahme
pytest, ruff, mypy grün. Abweichung zu expected.json <= 1e-9, Snapshot <= 1e-8.
test_contrast und test_no_placeholders grün.

## Stack
Python 3.12, uv, pydantic v2, pandas, numpy, openpyxl, NiceGUI (ui.leaflet),
pytest, hypothesis, ruff, mypy. Agent: Gemini hinter LLMProvider.
