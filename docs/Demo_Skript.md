# Demo-Skript (Live-Demo, 12 bis 15 Minuten)

Rahmen: Abschlusspräsentation am 06.01.2027, 45 Minuten, davon 12 bis 15 Minuten Demo.
Die Demo läuft lokal auf dem Rechner der Vortragenden (`make run`, Browser `http://127.0.0.1:8080`).
Keine öffentliche Instanz mit dem kostenlosen Gemini-Schlüssel.

## Vorbereitung (vor dem Termin)

| Punkt | Prüfung |
|---|---|
| Excel-Mappe | `data/excel/Thema1_Transportkonzept_v11_Beispieldaten.xlsx` vorhanden |
| Tests | `make test` grün, `make lint` grün |
| Start | `make run`, Seite lädt, Status "Plan zulässig" |
| Agent | `.env` mit `GEMINI_API_KEY`; ohne Schlüssel oder bei Ratenlimit greift der Demo-Modus |
| Rückfall | Bildschirmvideo der Demo auf dem Rechner; Start ohne Internet geprüft (Knoten-Kanten-Ansicht) |
| Excel | Testkopie der Excel geöffnet, Export-Datei griffbereit |

## Ablauf

| Schritt | Zeit | Aktion | Was zu sagen ist | Belegt |
|---|---|---|---|---|
| 1 | 2 min | Umschalter auf "Ist". Karte links, Kennzahlen | 2.266 Sendungen, jede einzeln: 306.924 kg CO₂e, 841.804 € Kosten, 812.758 Lkw-km. Linien sind Luftlinien zwischen PLZ-Schwerpunkten, schematisch | Qualität der Rechnung |
| 2 | 2 min | "M2 Bündelung", Tab Touren | Next-Fit je Tag und Startort: 428 Touren, 318 gebündelt. CO₂e −16,9 %, Kosten −24,9 %, Lkw-km −28,2 % | Funktionsfähigkeit |
| 3 | 2 min | "M3 Bahn + Bündelung", Karte rechts | 551 Bahn-Sendungen (gestrichelt), CO₂e −53,3 %, Lkw-km −67,7 %. Zielkonflikt: Servicegrad 75,7 %, weil die Bahn einen Tag länger braucht. Kosten gleich M2, weil A07 = 0 (Bahn kostet wie Lkw-Einzelversand) | Einordnung |
| 4 | 2 min | Eingabe, Tab Freitext, Fall "Einzelsendung per Freitext", Senden, dann "in die Eingabe übernehmen" | Der Agent übernimmt nur genannte Werte und ruft den Rechenkern; jede Zahl der Antwort stammt aus einer Werkzeugausgabe | Funktionsfähigkeit |
| 5 | 2 min | Schritt 2 Parameter: A01 auf 400, dann A05 auf 3, dann Zurücksetzen. Die Kennzahlen rechts ändern sich sofort | A01 = 400: 945 Bahn-Sendungen, −67,8 %. A05 = 3 über A06: keine Verlagerung, M3 gleich M2, Status-Chip "Plan prüfen" (Laufzeitregel verletzt) | Nachvollziehbarkeit |
| 5a | 2 min | Linie Stuttgart > Mainz anklicken, dann "Tour 1", dann Tab "Straße gegen Luftlinie" | Relationsdetail: 63 Einzelfahrten, davon 49 in Sammeltouren und 14 bleiben einzeln, CO₂e −26,4 %. Tour 1: 8 Einzelfahrten werden eine Tour mit Lkw 7,5t; alle vier Bedingungen erfüllt; 3 Sprinter würden die Tour dreimal fahren (860 kg statt 478 kg CO₂e). Straße gegen Luftlinie: empirischer Faktor gegen I01 | Nachvollziehbarkeit |
| 6 | 2 min | "Wie berechnet?" an der CO₂e-Kachel, dann Seite Analyse, Tab Agent-Spur | Formel, Parameter mit Quelle und Typ, Systemgrenze, Verifikation gegen Excel (Abweichung unter 1e-9) | Nachvollziehbarkeit |
| 7 | 2 min | Seite Analyse, Tab Prüfungen (20 Prüfungen, Referenzabgleich), zurück zur Eingabe, Export CSV, in Excel-Testkopie einfügen, eine Zahl nachrechnen | Python ist ein Port der Excel; Abnahme 1e-9 je Kennzahl und je Zeile | Qualität der Rechnung |
| 8 | 1 min | Freitext ohne Datum oder mit "schätz mal" | Der Agent verweigert die Schätzung ("nicht berechenbar, weil" mit Grund) oder die Antwort wird verworfen. Nur mit Gemini-Schlüssel live; im Demo-Modus die Negativtests in `tests/agent/test_agent.py` zeigen | Verlässlichkeit |

## Vorbereitete Agent-Fälle (Demo-Modus)

Die Schaltflächen im Tab Freitext setzen den Text. Im Demo-Modus wird nur genau dieser Text abgespielt.

1. Einzelsendung per Freitext: 800 kg auf 2 Paletten von 70173 Stuttgart nach 20095 Hamburg am 05.05.2025.
2. Bündelung vieler Sendungen: fünf Sendungen 68159 Mannheim nach 55116 Mainz am 03.03.2025.
3. Bahnfall: 2.400 kg von 79098 Freiburg im Breisgau nach 10115 Berlin am 10.06.2025.

## Rückfall

| Störung | Vorgehen |
|---|---|
| Kein Internet | Karte schaltet auf Knoten-Kanten-Ansicht; alle Rechnungen laufen lokal |
| Gemini nicht erreichbar oder Ratenlimit | Demo-Modus (automatisch nach drei Wiederholungen) oder `TK_DEMO_MODE=1` |
| App startet nicht | Bildschirmvideo; Excel-Ergebnisse auf der Folie |
