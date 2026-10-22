# Gesamtpaket für Claude Code: Transportplanungs-Artefakt (Excel-Modell v11)

Projekt: Seminar Planungsprozesse (BLO513/WPML733), Thema 1 "Nachhaltiges Transportkonzept", HWG Ludwigshafen
Stand: 20.10.2026 | Bezug: `Thema1_Transportkonzept_v11_Beispieldaten.xlsx`, `Artefakt_Projektplan.md` (Version 2)
Ersetzt: `Claude_Code_Prompts_Artefakt_v11.md` (dort fehlten GitHub-Workflow, Kartenkette, Design-System)

Verwendung: Diese Datei als `docs/Gesamtpaket.md` ins Repository legen. Abschnitt 12 ist der Inhalt von `CLAUDE.md`. Die Prompts in Abschnitt 13 werden nacheinander an Claude Code gegeben. Vor jedem Schritt zeigt Claude Code den Plan, nach jedem Schritt wird das Gate geprüft.

---

## 1. Festgelegte Entscheidungen

| Nr. | Entscheidung | Begründung |
|---|---|---|
| E1 | Excel v11 ist die fachliche Referenz, Python ist ein Port | Bewertung "Qualität der Rechnung": Nachprüfbarkeit gegen ein Modell, das die Gruppe versteht |
| E2 | Szenarien: Ist (Einzelversand), M2 (Bündelung), M3 (Bahnprüfung, dann Bündelung) | entspricht v11 |
| E3 | Rechenkern in Python 3.12, keine Zahl entsteht im Sprachmodell | Projekt- und Seminarregeln |
| E4 | Oberfläche NiceGUI mit `ui.leaflet`; Rückfall FastAPI plus Leaflet, falls Spike scheitert | Projektplan D2 |
| E5 | Karte zeigt Luftlinien zwischen Ortsschwerpunkten (wie Blatt `Routen`) | Das Modell rechnet nicht mit Straßengeometrie. Eine gezeichnete Straßenroute würde etwas zeigen, das nicht berechnet wird |
| E6 | Straßenrouting (ORS, OSRM) ist nicht Teil des Kerns. Optional nur als Darstellung (Prompt S19, Could), dann deutlich beschriftet | schützt die Abnahme gegen Excel |
| E7 | Ortsdaten aus Blatt `PLZ_Orte` (GeoNames, CC BY 4.0). Kein Geocoding zur Laufzeit | keine Limits, keine Schlüssel, offline lauffähig |
| E8 | Agent: Gemini (kostenlose Stufe) hinter `LLMProvider`, plus Demo-Modus mit aufgezeichneten Antworten | Projektplan D3 |
| E9 | Demo läuft lokal auf dem Rechner der Vortragenden. Keine öffentliche Instanz mit dem kostenlosen Schlüssel | Nutzungsbedingungen, Projektplan D3 (unsere Auslegung, vor Veröffentlichung prüfen) |
| E10 | Design: heller Modus, ruhig, eine Akzentfarbe, keine dekorativen Elemente | Abschnitt 7 |

---

## 2. Fachliche Referenz: Aufbau der Excel v11

### 2.1 Blätter

| Blatt | Funktion | Verwendung im Tool |
|---|---|---|
| `Dashboard` | Kacheln und 5 Diagramme | Vorbild für die Kennzahlenleiste, nicht nachbauen |
| `Overview & Results` | Methodenvergleich (Abschnitt 1), Sensitivität, 20 Prüfungen, Gesamtstatus `C162` | Referenz für `expected.json` und `checks.py` |
| `Assumptions` | Parameter A01 bis A14, B, C, I; Abschnitte A bis K; Schnittstelle J2.1 bis J2.8; Formelregister K2.1 bis K2.17; Tests T01 bis T10 | einzige Quelle für Parameter und Funktionsdefinitionen |
| `Input` | Eingabe ab Zeile 14 (bis 2.500 Zeilen), Rechenspalten je Sendung | Datenschema des Tools und Zeilenvergleich |
| `Touren` | Next-Fit-Tourbildung und Tourentscheidung | Referenz für `bundling.py` |
| `Routen` | Auswertung je Relation mit Koordinaten | Datenquelle der Karte |
| `PLZ_Orte` | Ortsdatenbank (GeoNames, Commit b4be5a6, Stand 31.07.2026) | Ortsauflösung |
| `Original_Data` | Originaldatensatz (Sendungs- und Tourdaten) | Rohdaten, nur lesen |

### 2.2 Eingabeschema (Blatt `Input`, Zeile 12)

| Spalte | Feld | Pflicht |
|---|---|---|
| A | Datum (JJJJ-MM-TT) | ja |
| B | Start (PLZ oder Ort) | ja |
| C | Ziel (PLZ oder Ort) | ja, außer Entfernung ist angegeben |
| D | Gewicht in kg (Zahl > 0) | ja |
| E | Sendungs-ID | optional |
| F | Entfernung in km (Zahl > 0) | optional, hat Vorrang |
| G | Paletten (Zahl > 0) | optional, leer: aus Gewicht abgeleitet |
| H | Frachtkosten in EUR | optional, leer: Kostenmodell |
| I | Eingabeprüfung | berechnet: "OK" oder Hinweis |

Das Tool übernimmt dieses Schema 1:1 (Import, Export, Formular).

### 2.3 Rechenspalten je Sendung (Auswahl, maßgeblich ist die Zellformel in der Excel)

Distanz: `W` Luftlinie (Haversine), `X` Relationstabelle, `Y` Straße (Näherung, Luftlinie × I01), `Z` Distanz verwendet, `AA` Quelle der Distanz.
Ist: `AB` Paletten verwendet, `AC` tkm, `AD` Fahrzeuge Einzel, `AE` Rang Fahrzeug, `AF` Fahrzeug Einzel, `AG` Auslastung, `AH` Lkw-km, `AI` CO2e (Fzg-km), `AJ` CO2e (tkm), `AK` Kosten Modell roh, `AL` Kosten Einzel.
Bahn (M3): `AM` Bahnkosten, `AN` Auf Bahn?, `AO` Bahn-CO2e.
Tourbildung (M2): `AP` Gruppe, `AQ` bündelbar, `AR` Rang in Gruppe, `AS` Sortierschlüssel, `AT` Zeile in Touren, `AU` Tour-Nr, `AV` Sendungen in Tour, `AW` Tour gebündelt.
Plan: `AX` Fahrzeuge geplant, `AY` Fahrzeug geplant, `AZ` Lkw-km geplant, `BA` CO2e geplant (Fzg-km), `BB` CO2e geplant (tkm), `BC` Kosten geplant, `BD` Ergebnis (Klartext).
Hilfsspalten: `BE` bis `BK` (Monat, Rang Start/Ziel, Engpass, Relation, Plausibilität).

### 2.4 Parameter (Cockpit `Input!D3:D9` und `Assumptions`)

| Kennung | Bedeutung | Wert (Stand v11) |
|---|---|---|
| A01 | Bahn-Mindestdistanz | 500 km |
| A02 | Vor-/Nachlauf | 100 km |
| A05 | Zusatzlaufzeit Bahn | 1 Tag |
| A07 | Kostenaufschlag Bahn | laut Assumptions |
| A08 | zulässige Kostensteigerung | 10 % |
| A10 | Umweg-Zuschlag | 20 % |
| C01 | Bahnfaktor (aktiv, Traktion Diesel) | 10,8 g/tkm |
| C02 | Lkw-Faktor für Vor-/Nachlauf (`p_VNL_Faktor`) | 335 g/tkm |
| C04 | Kostenkalibrierfaktor | 0,6465 (berechnet) |
| I01 | Straßenfaktor auf Luftlinie | 1,22 |
| `p_Schwelle` | Schwelle in der Bahnprüfung | 0,5 |

Alle weiteren Parameter (A03, A04, A06, A09, A11 bis A14, B, C, I) liest Claude Code aus `Assumptions`. Es gibt keine Konstante im Code.

### 2.5 Referenzwerte (gespeicherte Werte der Datei, N = 2.266)

| Kennzahl | Ist | M2 | M3 |
|---|---:|---:|---:|
| CO2e Fzg-km (kg) | 306.924,11 | 255.084,07 | 143.296,67 |
| Delta CO2e | | −16,89 % | −53,31 % |
| CO2e tkm, Kontrolle (kg) | 237.300,81 | 181.826,33 | 96.792,78 |
| Kosten (EUR) | 841.804,20 | 631.813,87 | 631.813,87 |
| Delta Kosten | | −24,95 % | −24,95 % |
| Fahrzeug-km | 812.757,62 | 583.221,01 | 262.563,03 |
| Delta Fahrzeug-km | | −28,24 % | −67,69 % |
| Bahnsendungen | 0 | 0 | 551 |
| Servicegrad | 100 % | 100 % | 75,68 % |
| Lkw-Fahrzeuge | 2.266 | | 545 |

Weitere Werte: 428 Touren, davon 318 gebündelt. Cockpit-Status "Plan zulässig", Gesamtprüfung `C162` "Alle Prüfungen bestanden". Die identischen Kosten von M2 und M3 sind konstruktionsbedingt und in der Arbeit zu erläutern.

---

## 3. Rechenmodell (Strukturformeln; die Zellformeln der Excel sind maßgeblich)

Notation: Sendung $i$, Tour $t$, Fahrzeug $f$, Masse $m$ in t, Distanz $d$ in km.

**Distanz** (Priorität: Eingabe, dann Relationstabelle, dann Näherung)

$$d_i = \begin{cases} d_i^{\text{Eingabe}} & \text{falls angegeben} \\ d_i^{\text{Relation}} & \text{falls vorhanden} \\ I_{01} \cdot h(\text{Start}_i, \text{Ziel}_i) & \text{sonst} \end{cases}$$

mit der Haversine-Distanz $h$ auf Basis der Koordinaten aus `PLZ_Orte`.

**Emissionen, Hauptrechnung (Fahrzeugkilometer)**

$$E_t = d_t \cdot e_f \cdot \lambda_t$$

$e_f$ in kg CO2e/km, $\lambda_t$ Auslastungsfaktor laut Assumptions.

**Emissionen, Kontrollrechnung (tkm, GLEC)**

$$E_t^{\text{tkm}} = m_t \cdot d_t \cdot g_f \cdot 10^{-3}$$

$g_f$ in g CO2e/tkm. Die Kontrolle dient der Plausibilität und ist nicht das Ergebnis.

**Bahn (M3)** Hauptlauf und Vor-/Nachlauf getrennt:

$$E_i^{\text{Bahn}} = \frac{m_i \left( A_{02}\, C_{02} + (d_i - A_{02})\, C_{01} \right)}{1000}$$

Strukturformel. Die exakte Formel steht in `Input!AO12` und `Assumptions` (Register K2.x) und ist wörtlich zu übernehmen.

**Kosten**

$$K_t = C_{04} \cdot K_t^{\text{Modell}}, \qquad C_{04} = \frac{\sum_{\text{OK},\,Fr_i>0} Fr_i}{\sum_{\text{OK},\,Fr_i>0} K_i^{\text{Modell}}}$$

**Zuordnung Tour auf Sendung (tkm-Anteil)**

$$E_i = E_t \cdot \frac{m_i d_i}{\sum_{j \in t} m_j d_j}$$

**Servicegrad**

$$S = 1 - \frac{N_{\text{Bahn}}}{N}$$

**Zulässigkeit** (Cockpit `Input!R8`): Plan zulässig, wenn die Kostenabweichung $\le A_{08}$ und die Laufzeitbedingung erfüllt ist.

**Rundung:** Vor dem Ranking der Fahrzeugwahl auf 6 Nachkommastellen, kaufmännisch (half away from zero). Python-`round` ist dafür ungeeignet, eigene Funktion über `decimal.Decimal` mit `ROUND_HALF_UP`.

**Methoden**
- Ist: jede Sendung einzeln, Fahrzeuganzahl und Rangregel laut `Input!AD:AF`.
- M2: Next-Fit je Tag und Startort, Entscheidung je Tour nach den vier Bedingungen in `Touren` und `Assumptions` (nicht aus diesem Dokument ableiten).
- M3: zuerst Bahnprüfung (Distanz über A01, Laufzeit, Kosten, Schwelle), danach M2 auf den verbleibenden Lkw-Sendungen.

---

## 4. Stack und Lizenzen

### 4.1 Software

| Zweck | Wahl | Lizenz (vor Abgabe verifizieren) |
|---|---|---|
| Sprache, Paketmanager | Python 3.12, uv | PSF, MIT/Apache |
| Modelle, Validierung | pydantic v2 | MIT |
| Daten | pandas, numpy, openpyxl | BSD, MIT |
| Oberfläche | NiceGUI (Quasar, Tailwind-Klassen) | MIT |
| Karte | Leaflet über `ui.leaflet` | BSD-2 |
| Tests | pytest, hypothesis | MIT, MPL-2.0 |
| Qualität | ruff, mypy | MIT |
| Agent | Gemini API (kostenlose Stufe) hinter `LLMProvider` | Nutzungsbedingungen Google |
| Schrift | Geist (Rückfall Inter), lokal eingebunden | SIL OFL |
| Versionskontrolle, CI | GitHub, GitHub Actions | |

### 4.2 Daten und Kartendienste

| Quelle | Verwendung | Pflicht |
|---|---|---|
| GeoNames über `zauberware/postal-codes-json-xml-csv` (CC BY 4.0) | `PLZ_Orte` | Namensnennung in UI-Fußzeile und Arbeit: "Postleitzahl- und Ortsdaten: GeoNames, geonames.org, CC BY 4.0" |
| OpenStreetMap-Standardkacheln (ODbL für die Daten) | Hintergrundkarte | Attribution "© OpenStreetMap contributors" sichtbar; Nutzungsrichtlinie der Kachelserver beachten (kein Dauerbetrieb, kein Vorabladen, eigener Referer) |
| OpenFreeMap (optional, Upgrade) | hellerer Vektorstil | Attribution laut Anbieter; Stilname und Einbindung vor Nutzung prüfen, nicht Teil des MVP |
| PMTiles (optional) | Offline-Rückfall | nur falls Kacheln für die Demo vorab bereitgestellt werden müssen; Quelle und Lizenz vorab klären |

Nicht verwendet: Nominatim, ORS und OSRM im Kern. Grund: E5 bis E7.

### 4.3 Entwicklungswerkzeuge

| Werkzeug | Nutzung |
|---|---|
| Claude Code | Umsetzung nach den Prompts in Abschnitt 13 |
| Claude Pro (Chat) | Planung, Review, Texte. Enthält keinen API-Zugang |
| GitHub Student Developer Pack | Repository, Codespaces als Rückfallumgebung, Copilot Student. Umfang und Laufzeit bei GitHub Education prüfen |
| Microsoft Excel | Neuberechnung der Referenz und Round-Trip-Test |
| Google AI Studio | API-Schlüssel, aktuelle Modellnamen und Limits |

---

## 5. GitHub-Workflow

### 5.1 Repository

| Punkt | Festlegung |
|---|---|
| Sichtbarkeit | privat, Gruppenmitglieder als Collaborators |
| Name | `transportkonzept-artefakt` |
| Hauptzweig | `main`, geschützt: Merge nur per Pull Request, CI muss grün sein, mindestens 1 Review durch ein anderes Gruppenmitglied |
| Arbeitszweige | `feat/<prompt-nr>-<kurzname>`, z. B. `feat/s08-bundling` |
| Commits | `feat:`, `fix:`, `test:`, `docs:`, `chore:`; Verweis auf Gate, z. B. `feat: Next-Fit bundling (G4)` |
| Daten im Repo | `data/excel` und `data/raw` nur, wenn die Seminardaten weitergegeben werden dürfen (Datensatz laut Projektplan synthetisch und anonymisiert). Im Zweifel in `.gitignore` und nur lokal halten |
| Secrets | `GEMINI_API_KEY` nur in `.env` (lokal) und als Actions-Secret. Nie im Chat, Code oder Verlauf |
| Lizenz | Repository bleibt privat und ohne Lizenzdatei, bis die Gruppe entscheidet. Drittlizenzen in `THIRD_PARTY.md` |
| Release | Tag `v1.0-abgabe` vor dem 04.01.2027, ZIP des Standes für Olat |

### 5.2 Pull-Request-Vorlage (`.github/pull_request_template.md`)

```markdown
## Zweck
Prompt-Nr.: S__   Gate: G__

## Änderungen
-

## Nachweis
- [ ] pytest grün
- [ ] ruff und mypy grün
- [ ] Abweichung zu expected.json <= 1e-9 (falls Rechenkern betroffen)
- [ ] keine Parameter im Code, keine Platzhaltertexte
- [ ] Prompt-Log ergänzt (docs/prompt_log.md)
```

### 5.3 CI (`.github/workflows/ci.yml`)

```yaml
name: ci
on:
  pull_request:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --all-extras
      - run: uv run ruff check .
      - run: uv run mypy src
      - run: uv run pytest -q
```

Hinweis: Action-Versionen vor Nutzung gegen die aktuelle Dokumentation prüfen. CI läuft ohne Excel-Original, wenn die Daten nicht im Repo liegen: Tests mit Referenzdaten dann mit `pytest.mark.skipif` kennzeichnen und lokal ausführen.

### 5.4 Weitere Dateien

`.gitignore` (mindestens `.env`, `.venv`, `__pycache__`, `data/raw`, `data/excel` falls nicht freigegeben, `*.xlsx` außerhalb von `tests/fixtures`), `.env.example` ohne Wert, `THIRD_PARTY.md` (Tabelle 4.1 und 4.2), `docs/prompt_log.md`, `README.md` (Start in unter 10 Minuten).

---

## 6. Repository-Struktur

```
transportkonzept-artefakt/
  CLAUDE.md
  README.md
  THIRD_PARTY.md
  pyproject.toml                 # uv, Python 3.12
  Makefile                       # run, test, lint, reference
  .env.example
  .github/{workflows/ci.yml, pull_request_template.md}
  data/
    excel/                       # Original, schreibgeschützt
    raw/                         # Original_Data
    reference/                   # expected.json, sendungen_ref.csv, snapshot.json
    exports/                     # Ausgabe im Input-Schema
  scripts/make_reference.py
  src/tk/
    models.py  assumptions.py  geo.py  distance.py  emissions.py  costs.py
    vehicle.py  bundling.py  rail.py  scenarios.py  checks.py  explain.py  export.py
    agent/    provider.py  tools.py  orchestrator.py  trace.py  demo.py
    ui/       app.py  theme.py  map_view.py  panels/
    assets/   fonts/Inter-*.woff2
  tests/      core/  e2e/  agent/  test_contrast.py  test_no_placeholders.py
  docs/       Gesamtpaket.md  Annahmen.md  Demo_Skript.md  prompt_log.md
```

Regel: `src/tk` (Kern) kennt weder UI noch Agent. Jede Funktion J2.x aus `Assumptions` entspricht einer Funktion im Kern, mit Verweis auf das Register K2.x im Docstring.

---

## 7. Design-System (heller Modus, ruhig, hochwertig)

### 7.1 Leitsätze

1. Minimaler Website-Look: warmes Off-White, viel Weißraum, Haarlinien statt Karten. Dezente, aufeinander abgestimmte Pastelltöne (Salbei, Himmel, Pfirsich, Lavendel, Butter, Rosé) als Punkte, Pillen und Flächen; Schrift darauf immer im passenden dunklen Ton. Farbe ist nie die einzige Information.
2. Tiefgrün `--accent` für Reduktion, Akzentpunkt und Fokus; dunkle Tinte `--text` für primäre Aktionen (Pille mit Pfeil). Die Vergleichsbasis (Ist) erhält Pfirsich, Bahn Himmelblau.
3. Hierarchie durch Typografie: sehr große Headline, nummerierte Abschnitte (Kicker „01“ mit kurzer Linie), Titel mit Akzentpunkt.
4. Eine Aussage pro Seite. Seite Eingabe: Ergebnis als Headline, Kennzahlenreihe, dann 01 Sendungen, 02 Parameter, 03 Karte. Seite Analyse: Tabellen, Szenarienvergleich, Erklärung, Prüfungen, Agent-Spur.
5. Bewegung dezent und funktional: Abschnitte blenden beim Laden ein, neu berechnete Zahlen gleiten ein, Pfeile und Unterstriche reagieren auf Hover (200 bis 700 ms). `prefers-reduced-motion: reduce` schaltet jede Bewegung ab.
6. Jedes Element hat eine Funktion. Keine Illustrationen, Verläufe, Icons ohne Beschriftung, Emojis, Platzhaltertexte.

### 7.2 Farbtokens (Kontraste mit WCAG-Formel berechnet)

| Token | Hex | Verwendung | Kontrast |
|---|---|---|---|
| `--bg` | `#FAF8F5` | Seitenhintergrund (warmes Off-White) | Text 13,9 : 1; `--muted` 5,9 : 1 |
| `--surface` | `#FFFFFF` | Eingabefelder, aktive Pillen, Dialoge | Text 14,8 : 1 |
| `--canvas` | `#F3F0EB` | Pillen-Hintergrund, Hover, Tabellenzeilen | Text 13,0 : 1; `--muted` 5,5 : 1 |
| `--line` | `#E6E1D9` | Haarlinien zwischen Abschnitten und Kennzahlen | trägt keine Information |
| `--line-strong` | `#D8D2C8` | Rahmen von Eingabefeldern | trägt keine Information |
| `--text` | `#1F2933` | Fließtext, Zahlen, primäre Schaltfläche | 14,8 : 1 auf Weiß; Weiß darauf 14,8 : 1 |
| `--muted` | `#56616E` | Beschriftungen, Einheiten, Kicker | 6,3 : 1 auf Weiß, mindestens 5,1 : 1 auf jedem Pastellton |
| `--accent` | `#1F6F5F` | Reduktion, Akzentpunkt, Fokus | 6,0 : 1 auf Weiß; 5,7 : 1 auf `--bg` |
| `--accent-tint` | `#E3EEE7` | Salbei: CO₂e, Abschnitt 01, Reduktion, geänderte Felder | Text 12,4 : 1; `--accent` darauf 5,0 : 1 |
| `--base` | `#9A4F2F` | Ist, Zunahme | 5,9 : 1 auf Weiß; 4,9 : 1 auf Tint |
| `--base-tint` | `#F6E6DB` | Pfirsich: Fahrzeug-km, Ist, Zunahme | Text 12,1 : 1 |
| `--info` | `#2F6FA8` | Bahn | 5,3 : 1 auf Weiß; 4,6 : 1 auf Tint |
| `--info-tint` | `#E9F0F7` | Himmel: Kosten, Bahn, Abschnitt 03 | Text 12,8 : 1 |
| `--violet` | `#5B4BB0` | Schrift auf Lavendel | 6,8 : 1 auf Weiß; 5,5 : 1 auf Tint |
| `--violet-tint` | `#E9E5F4` | Lavendel: Servicegrad, Abschnitt 02 | Text 11,9 : 1 |
| `--note-tint` | `#F5EED8` | Butter: Annahmen, Hinweise | Text 12,7 : 1; `#8A5A00` darauf 5,1 : 1 |
| `--danger` | `#B42318` | Fehler, Plan prüfen | 6,6 : 1 auf Weiß; 5,4 : 1 auf Rosé `#F7E4E2` |

Kartenlinien (müssen gegen die Karte mindestens 3 : 1 erreichen):

| Ebene | Farbe | Stil |
|---|---|---|
| Ist, Einzelversand | `#B5694A` | durchgezogen, Breite nach Anzahl Sendungen |
| Plan, Lkw (gebündelt) | `#2D8470` | durchgezogen, Breite nach tkm |
| Plan, Bahn | `#2F6FA8` | gestrichelt (Muster zusätzlich zur Farbe) |

Regeln: Auf Tönen dunkler Text. Weißer Text nur auf `--accent`, `--text` und `--danger`. Keine Information nur über Farbe: immer zusätzlich Beschriftung, Muster oder Linienstärke. `tests/test_contrast.py` prüft alle Paare mit der WCAG-Formel (Text mindestens 4,5 : 1, Linien mindestens 3 : 1) und ist Abnahmekriterium.

### 7.3 Typografie, Raster, Form

| Element | Festlegung |
|---|---|
| Schrift | Geist (variabel, lokal, SIL OFL), Rückfall Inter und `system-ui`; Zahlen mit `font-variant-numeric: tabular-nums` |
| Größen | Headline 44 bis 72 px / 600, Laufweite −0,045 em; Abschnittstitel 34 px / 600; Kennzahl 30 bis 40 px / 600; Fließtext 15 px / 400; Einleitung 18 px in `--muted`; Beschriftung 13 px / 500; Kicker 12 px, Großbuchstaben, Laufweite +0,08 em |
| Raster | Inhalt höchstens 1280 px, 12 Spalten, Abstand 32 px; Abschnitte 56 px oben und unten; Abschnittskopf 4 Spalten (bleibt beim Scrollen stehen), Inhalt 8 Spalten |
| Form | Keine Karten auf der Seite, Gliederung durch 1 px Haarlinien `--line`. Eingaben Radius 12 px, Schaltflächen, Umschalter, Status und Deltas als Pillen. Schatten nur `--shadow-sm` (`0 1px 2px`) für aktive Pillen |
| Zahlenformat | deutsch: Tausenderpunkt, Dezimalkomma, Einheit mit schmalem Leerzeichen (`306.924 kg CO2e`); Prozent mit Vorzeichen (`−53,3 %`) |
| Fokus | 2 px Ring in `--accent`, nie entfernen |

CSS-Grundlage (in `ui/theme.py` per `ui.add_css` einbinden):

```css
:root {
  --bg:#F6F7F8; --surface:#FFFFFF; --line:#E3E6EA;
  --text:#1F2933; --muted:#56616E;
  --accent:#1F6F5F; --accent-tint:#E8F3EE;
  --base:#9A4F2F; --base-tint:#F8EBE4;
  --info:#2F6FA8; --info-tint:#E6EFF8;
  --note-tint:#FAF3DC; --danger:#B42318;
}
body { background:var(--bg); color:var(--text); font-family:Inter, system-ui, sans-serif; font-size:14px; }
.tk-card { background:var(--surface); border:1px solid var(--line); border-radius:12px; padding:16px; }
.tk-label { color:var(--muted); font-size:12px; font-weight:500; }
.tk-kpi { font-size:28px; font-weight:600; font-variant-numeric:tabular-nums; }
:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
.leaflet-tile-pane { filter:grayscale(0.85) contrast(0.95) brightness(1.04); }
```

Der Filter auf der Kachelebene dämpft die Standardkarte, ohne Anbieter oder Attribution zu ändern.

### 7.4 Layout

Seite Eingabe (`/`):

```
TK.  ( Eingabe | Analyse )      CO2e −53,3 %  Kosten −24,9 %  ...   ( Analyse öffnen → )   feste Leiste
-------------------------------------------------------------------------------------------
−53,3 % CO2e.                                          ( Ist | M2 | M3 )
M3 Bahn + Bündelung gegen Einzelversand: ...           ● Plan zulässig

CO2e (Fzg-km)    | Kosten          | Fahrzeug-km     | Servicegrad
143.297 kg       | 631.814 €       | 262.563 km      | 75,7 %
(−53,3 % gegen Ist)  Ist: ...      | ...             | Bahn 24,3 %
-------------------------------------------------------------------------------------------
01 ── SENDUNGEN          | Formular | Einfügen / CSV | Freitext
Sendungen erfassen.      | Datum  Gewicht / Start  Ziel / ( Sendung hinzufügen → )
-------------------------------------------------------------------------------------------
02 ── PARAMETER          | BAHNVERLAGERUNG (M3)  A01  A02  A05  A04
Parameter anpassen.      | BÜNDELUNG (M2)  A10  A09 | KOSTEN  A08 | DISTANZ  I01, ORS
-------------------------------------------------------------------------------------------
03 ── KARTE
Vorher und nachher.      (Karte volle Breite)
-------------------------------------------------------------------------------------------
Weiter zur Analyse →     (Zusammenfassung, Attribution OSM, GeoNames, Datenstand)
```

Die feste Leiste zeigt die kompakten Kennzahlen, sobald die Kennzahlenreihe oben aus dem Bild scrollt; so bleibt jede Änderung in Schritt 02 sofort sichtbar.

Seite Analyse (`/analyse`, Tab per `?tab=sendungen|touren|szenarien|erklaerung|pruefungen|agent`): gleiche Leiste, Headline „Analyse.“, die Tabs als nummerierte Pillen 01 bis 06, Tabellen ohne Karten. Beide Seiten teilen den Stand je Browser (Sendungen, Parameter, Szenario, Agent-Spur).

Breakpoints: Abschnittskopf und Inhalt nebeneinander ab 1100 px, darunter untereinander; Kennzahlen vierspaltig ab 1100 px, darunter 2 × 2; in der Leiste unter 1280 px nur Bezeichnung und Delta. Mindestbreite 1024 px (Präsentationsbeamer), Mobilgeräte sind nicht Ziel.

### 7.5 Komponenten

| Komponente | Verhalten |
|---|---|
| Szenario-Umschalter | Pillen Ist, M2, M3 auf `--canvas`. Aktiv: weiße Pille, Schrift 600, `aria-pressed`. Wechsel aktualisiert Headline, Kennzahlen, Leiste, Karte, Tabellen |
| Status-Chip | Abbild von `Input!R8`: "Keine Eingabe" (neutral), "Eingabe prüfen" (`--note-tint`), "Plan zulässig" (`--accent-tint`), "Plan prüfen" (`--danger`-Tint). Immer mit Text |
| Kennzahl | Ohne Karte in einer Reihe mit Haarlinien. Label mit Punkt im eigenen Pastellton (CO₂e Salbei, Kosten Himmel, Fahrzeug-km Pfirsich, Servicegrad Lavendel), Wert Plan (bis 40 px), darunter Delta als Pille mit Vorzeichen und Text "gegen Ist" sowie "Ist: Wert". Pille: Reduktion `--accent` auf `--accent-tint`, Zunahme `--base` auf `--base-tint`. Das Szenario steht in der Headline. Link "Wie berechnet?" öffnet Erklärung (Formel, Parameter, Quelle, Verifikationsstatus) |
| Eingabeformular | Abschnitt 01. Pflichtfelder A bis D wie in Excel, mit "(Pflicht)" beschriftet. Beschriftung über dem Feld, Einheit im Feld, Hilfetext darunter. Hinweistexte aus Spalte I. Inline-Validierung, Fehler mit Ursache und nächstem Schritt |
| Parameterpanel | Abschnitt 02, Felder im Dreierraster. Gruppen Bahnverlagerung (M3), Bündelung (M2), Kosten, Distanz. Zahlenfeld mit ID, Name und Einheit aus `Assumptions`, Anteile als Prozent. Hilfetext mit Wirkung und Standardwert; Tooltip mit Typ, Quelle, Zelle. Geänderte Felder: Fläche `--accent-tint` und Text "Geändert, Standard: Wert". Schrittstatus nennt die Zahl geänderter Werte. Link "Zurücksetzen". Änderung rechnet sofort neu |
| Karte | Siehe Abschnitt 9 |
| Tabellen | Sortierbar, feste Kopfzeile, Zahlen rechtsbündig, Klartext-Ergebnis je Sendung (Spalte `BD`), Filter nach Tour und Verkehrsträger |
| Szenarienvergleich | Tabelle Ist, M2, M3 plus ein gruppiertes Balkendiagramm (Delta CO2e, Kosten, Fahrzeug-km). Kein weiteres Diagramm |
| Prüfungen | 20 Checks als Liste mit Status, Gesamtstatus oben, Abgleich gegen `expected.json` |
| Agent-Spur | chronologische Liste der Werkzeugaufrufe mit Ein- und Ausgabe, einklappbar |

Zustände (jeweils gestaltet): leer (eine klare Aktion, z. B. "Beispieldaten laden" oder "Sendungen einfügen"), lädt (dezenter Fortschritt, keine Spinner-Animation über 1 s), Fehler (Ursache plus nächster Schritt), Erfolg (knappe Bestätigung).

### 7.6 Ausdrücklich nicht enthalten

Dunkelmodus, Animationen ohne Funktion (Endlosschleifen, Parallaxe, Konfetti), Verläufe, Illustrationen, Emojis, Tortendiagramme, Tachometer, 3D, Konfetti, Willkommensbanner, Cookie-Hinweise, Anmeldung, Mehrsprachigkeit, Platzhaltertexte (`Lorem`, `TODO`, `xxx`, `Beispiel`). `tests/test_no_placeholders.py` durchsucht das Repository danach.

---

## 8. Funktionsumfang (MoSCoW, auf v11 bezogen)

**Must**
1. Eingabe: Formular, Einfügen aus Excel/CSV im Schema von `Input!A:H`, Validierung wie Spalte I.
2. Rechnung Ist, M2, M3 nach Abschnitt 3, identisch zur Excel (Abnahme 1e-9).
3. Fahrzeugwahl nach Rangregel, Bahnprüfung, Bündelung Next-Fit.
4. Kennzahlen CO2e (Fzg-km, Kontrolle tkm), Kosten, Fahrzeug-km, Servicegrad mit Delta.
5. Karte mit Vorher und Nachher aus `Routen`.
6. Erklärung je Kennzahl (Formel, Parameter, Quelle, Verifikation).
7. 20 Prüfungen und Gesamtstatus.
8. Export im Input-Schema (CSV und XLSX) für den Round Trip in die Excel.

**Should**
1. Freitext-Eingabe über den Agenten.
2. Parameterregler mit Sofortberechnung und Sensitivitätsansicht (13 Szenarien aus dem Snapshot).
3. Agent-Spur im UI.
4. Demo-Modus mit drei vorbereiteten Fällen.
5. Referenzabgleich-Seite (Python gegen Excel je Kennzahl).

**Could**
1. Straßengeometrie als reine Darstellung (E6).
2. PDF-Kurzbericht je Szenario.
3. OpenFreeMap-Stil, PMTiles-Offlinekarte.

**Won't**
Echtzeitverkehr, Maut, Mehrbenutzerbetrieb, Anmeldung, Datenbank, Faktorenrecherche zur Laufzeit.

---

## 9. Karte

| Punkt | Festlegung |
|---|---|
| Datenquelle | Blatt `Routen`: Start/Ziel-Koordinaten (E bis H), Sendungen (I), Gewicht (J), Distanz (K), tkm (M), CO2e Ist/Plan (N, O), Kosten (Q, R) |
| Geometrie | gerade Linie zwischen Ortsschwerpunkten, Beschriftung "Luftlinie, schematisch" in der Legende |
| Ansicht | Zwei Karten nebeneinander (Vorher, Nachher) mit synchronem Zoom, oder Umschalter. Swipe-Plugin ist in NiceGUI ungetestet und kein Pflichtbestandteil |
| Kodierung | Farbe plus Linienstärke plus Muster (Abschnitt 7.2). Legende mit Text |
| Popup | Relation, Sendungen, Gewicht, Distanz und Quelle der Distanz, CO2e Ist/Plan, Delta, Kosten |
| Kacheln | OSM-Standard mit Filter (7.3), Attribution fest eingeblendet |
| Rückfall ohne Netz | Knoten-Kanten-Ansicht (SVG) aus denselben Koordinaten, automatisch bei Kachelfehler |
| Spike | Vor S14: Polylinie, Popup, Strichmuster, synchroner Zoom mit `ui.leaflet` prüfen. Falls nicht möglich, FastAPI plus Leaflet (Kern bleibt unverändert) |

---

## 10. Agent

Grundsatz: Das Modell rechnet nie. Es versteht Eingaben, ruft Werkzeuge auf und gibt Werkzeugausgaben wortgetreu weiter.

| Werkzeug | Zweck |
|---|---|
| `parse_shipments` | Freitext oder Tabelle in Sendungen nach `Input`-Schema, fehlende Felder melden |
| `validate_shipments` | Prüfung wie Spalte I |
| `plan_scenarios` | Ist, M2, M3 rechnen |
| `get_route_summary` | Relation aus `Routen` |
| `compare_scenarios` | Kennzahlen und Deltas |
| `explain_result` | Formel, Parameter, Quelle zu einer Kennzahl |

Leitplanken: Zahlen nur aus Werkzeugausgaben (Test per Regex-Abgleich). Fehlende Daten führen zu Rückfrage oder "nicht berechenbar, weil [Grund]". Jeder Aufruf wird protokolliert. Wiederholung mit Wartezeit bei Ratenlimit, danach Wechsel in den Demo-Modus. Schnittstelle `LLMProvider` kapselt den Modellzugang. Vor der Implementierung SDK, Funktionsaufrufe und Modellnamen der kostenlosen Stufe gegen die dann aktuelle Dokumentation prüfen. Negativtests: unbekannter Ort, Gewicht null, fehlende Pflichtfelder, Aufforderung zum Schätzen, Aufforderung, den Kern zu umgehen.

Datenschutz: Die kostenlose Stufe darf Eingaben zur Produktverbesserung nutzen. Nur synthetische Daten an das Modell senden.

---

## 11. Qualitätssicherung und Gates

### 11.1 Tests

| Test | Inhalt |
|---|---|
| T01 bis T10 | Die Tests aus `Assumptions` (Abschnitt Tests) werden von Claude Code gelesen und 1:1 als pytest-Tests angelegt. Die Zuordnung der Nummern kommt aus der Excel, nicht aus diesem Dokument |
| Zeilenvergleich | Alle 2.266 Sendungen: Python gegen `sendungen_ref.csv` je Ergebnisspalte, relative Abweichung ≤ 1e-9 |
| Kennzahlen | Abschnitt 2.5 gegen `expected.json`, ≤ 1e-9 |
| Snapshot | 13 Sensitivitätsszenarien, ≤ 1e-8 |
| Eigenschaften | hypothesis: keine Tour überschreitet Nutzlast oder Palettenkapazität, jede Sendung genau einer Tour oder Bahn zugeordnet, Summe der Zuordnung = Tourwert |
| Rundung | Gleichstand nach Rundung, Excel-Verhalten |
| Kontrast | Farbpaare (7.2) |
| Platzhalter | Suche nach `Lorem`, `TODO`, `xxx`, `Beispiel` im Repository |
| Agent | Negativtests (Abschnitt 10) |
| Round Trip | Export, Import in Testkopie der Excel, Ergebnis gleich Python |

### 11.2 Gates

| Gate | Nach Prompt | Kriterium |
|---|---|---|
| G0 | S0 | Repo, Schutzregeln, CI grün |
| G1 | S1 | Toolchain grün |
| G2 | S2 | Referenz entspricht Abschnitt 2.5 |
| G3 | S3 bis S7 | Einzelmodule ≤ 1e-9 |
| G4 | S8, S9 | 428 Touren, 318 gebündelt, 551 Bahnsendungen |
| G5 | S10, S11 | Alle Kennzahlen, Snapshot ≤ 1e-8, 20 Checks, Status "Plan zulässig" |
| G6 | S12 bis S14 | UI, Karte, Kontrasttest, keine Platzhalter |
| G7 | S15, S16 | Agent nur mit Werkzeugzahlen, Export-Round-Trip |
| G8 | S17, S18 | Doku, Prompt-Log, unabhängiger Review bestanden |

---

## 12. Inhalt von `CLAUDE.md`

```markdown
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
Tokens und Regeln: docs/Gesamtpaket.md Abschnitt 7. Keine Dekoration, keine Animation
außer 150 ms Hover/Fokus, keine Platzhaltertexte, Farbe nie als einzige Information.
Kartenlinien: Luftlinie, schematisch. Attribution OSM und GeoNames immer sichtbar.

## Abnahme
pytest, ruff, mypy grün. Abweichung zu expected.json <= 1e-9, Snapshot <= 1e-8.
test_contrast und test_no_placeholders grün.

## Stack
Python 3.12, uv, pydantic v2, pandas, numpy, openpyxl, NiceGUI (ui.leaflet),
pytest, hypothesis, ruff, mypy. Agent: Gemini hinter LLMProvider.
```

---

## 13. Prompts für Claude Code

Startprompt (einmalig):

```
Lies CLAUDE.md und docs/Gesamtpaket.md vollständig. Fasse in höchstens zehn Sätzen zusammen,
was gebaut wird, und nenne Unklarheiten. Ändere noch nichts.
```

### S0 GitHub-Setup
```
Zeige zuerst den Plan. Dann: richte das Repository gemäß Abschnitt 5 ein: .gitignore, .env.example,
.github/pull_request_template.md, .github/workflows/ci.yml, THIRD_PARTY.md (Tabellen 4.1 und 4.2),
docs/prompt_log.md. Schlage die Branch-Schutzregeln für main als Liste vor (ich setze sie im
GitHub-Interface selbst). Prüfe die aktuellen Versionen der Actions in ci.yml. Lege keine Daten und
keine Schlüssel an.
```
Gate G0: CI läuft auf einem leeren Pull Request grün.

### S1 Projektgerüst
```
Zeige den Plan. Lege das uv-Projekt (Python 3.12) mit der Struktur aus Abschnitt 6 an: pyproject.toml,
Makefile (run, test, lint, reference), Paketordner src/tk mit leeren Modulen und Docstrings, tests/.
Installiere die Pakete aus Abschnitt 4.1. Konfiguriere ruff, mypy (strict für src/tk) und pytest.
```
Gate G1: `uv run pytest`, `ruff`, `mypy` laufen.

### S2 Referenz erzeugen
```
Schreibe scripts/make_reference.py. Es liest data/excel/*.xlsx mit openpyxl (read_only, data_only=True,
niemals speichern) und erzeugt in data/reference/: expected.json (Overview & Results Abschnitt 1,
Cockpit Input!D3:R9, Assumptions D49 bis D53, Gesamtstatus C162), sendungen_ref.csv (Blatt Input ab
Zeile 14, alle Ergebnisspalten mit Spaltenkopf aus Zeile 12), snapshot.json (Sensitivitätstabelle,
13 Szenarien). Dokumentiere jeden Zellbezug im Code. Gib die Kennzahlen aus und vergleiche sie mit
Abschnitt 2.5 des Gesamtpakets.
```
Gate G2.

### S3 Modelle und Parameterlader
```
Implementiere src/tk/models.py (pydantic v2: Shipment gemäß Input!A:H, Assumptions, Tour, Result)
und assumptions.py. Lade alle Parameter A01 bis A14, B, C, I aus dem Blatt Assumptions mit Einheit
und Quelle. Keine Defaults im Code. Lege Tests aus Assumptions (Abschnitt Tests) an, soweit sie die
Parameter betreffen, mit der Excel-Nummerierung T01 bis T10.
```

### S4 Geodaten und Distanz
```
Implementiere geo.py (Haversine, Laden von PLZ_Orte mit Auflösung PLZ/Ort/mehrdeutig/nicht gefunden
wie in Input!L und R) und distance.py (Priorität Eingabe, Relationstabelle, Haversine * I01).
Vergleiche Spalten W, X, Y, Z, AA für alle Zeilen mit sendungen_ref.csv.
```

### S5 Emissionen
```
Implementiere emissions.py: Hauptrechnung (Fzg-km), Kontrollrechnung (tkm), Bahn-CO2e (Input!AO).
Übernimm die Zellformeln wörtlich. Jede Funktion erhält einen Docstring mit Formel in LaTeX,
Annahmen, Quelle, Systemgrenze und Register-Verweis K2.x. Vergleiche AI, AJ, AO.
```

### S6 Kosten
```
Implementiere costs.py: Kostenmodell roh, Kalibrierfaktor C04 (Assumptions D52), Kosten Einzel,
Bahnkosten. Vergleiche AK, AL, AM. C04 muss 0,6465 ergeben.
```

### S7 Fahrzeugwahl
```
Implementiere vehicle.py: Fahrzeuganzahl, Rangregel, Auslastung. Implementiere
round_half_away(x, 6) über Decimal. Schreibe Tests für Gleichstand nach Rundung und einen
hypothesis-Test auf Monotonie. Vergleiche AB bis AH.
```

### S8 Bündelung (M2)
```
Implementiere bundling.py gemäß Blatt Touren: Gruppierung, Next-Fit je Tag und Startort,
Entscheidung je Tour nach den vier Bedingungen. Lies die Bedingungen aus Touren und Assumptions,
erfinde nichts. Vergleiche AP bis AW und AX bis BC. Erwartung: 428 Touren, davon 318 gebündelt,
Fahrzeug-km M2 = 583.221,01.
```
Gate G4 (teilweise).

### S9 Bahnprüfung (M3)
```
Implementiere rail.py: Distanzschwelle A01, Laufzeit A05, Kostenbedingung A08, Schwelle p_Schwelle,
Traktion Diesel oder elektrisch. Vergleiche AM bis AO. Erwartung: 551 Bahnsendungen.
```

### S10 Szenarien und Allokation
```
Implementiere scenarios.py: Ist, M2, M3, Zuordnung auf Sendungen (tkm-Anteil), Servicegrad,
Zulässigkeit (Input!R8). Alle Kennzahlen aus Abschnitt 2.5 müssen innerhalb 1e-9 liegen,
der Snapshot innerhalb 1e-8. Gib bei Abweichung Zelle, Spalte und Zeile aus.
```
Gate G5 (teilweise).

### S11 Prüfungen
```
Implementiere checks.py: die 20 Prüfungen aus Overview & Results mit Gesamtstatus (C162) und
Erklärungstexten. Implementiere explain.py: Formel, Parameter, Quelle und Verifikationsstatus je
Kennzahl. Erwartung: "Alle Prüfungen bestanden".
```
Gate G5.

### S12 Design-System
```
Lies Abschnitt 7 des Gesamtpakets. Implementiere ui/theme.py (CSS-Tokens, Inter lokal, Komponenten-
Klassen tk-card, tk-label, tk-kpi, Status-Chip, Szenario-Umschalter) und tests/test_contrast.py
(WCAG-Formel, alle Paare aus 7.2) sowie tests/test_no_placeholders.py. Baue eine Vorschauseite mit
allen Komponenten und Zuständen (leer, lädt, Fehler, Erfolg), ohne erfundene Daten.
```

### S13 Eingabe, Kennzahlen, Tabellen
```
Baue ui/app.py gemäß Layout 7.4: Kopfzeile mit Szenario-Umschalter und Status-Chip, Eingabepanel
(Formular, Einfügen, CSV im Schema Input!A:H, Validierung wie Spalte I), Parameterpanel mit
Standardwerten aus Assumptions, vier Kennzahlenkacheln mit Delta und "Wie berechnet?", Tabs
Sendungen, Touren, Szenarien (Tabelle plus ein Balkendiagramm), Erklärung, Prüfungen. Beim Start
sind die Beispieldaten der Excel geladen (keine erfundenen Werte). Alle Zahlen kommen aus src/tk.
```

### S14 Karte
```
Spike zuerst: prüfe mit ui.leaflet Polylinie, Popup, Strichmuster, Linienstärke, synchronen Zoom
zweier Karten. Melde das Ergebnis. Bei Erfolg implementiere ui/map_view.py gemäß Abschnitt 9 mit
Daten aus Routen (Luftlinien, Legende, Attribution, SVG-Rückfall bei Kachelfehler). Bei Misserfolg
schlage den Rückfall FastAPI plus Leaflet vor und warte auf Freigabe.
```

### S15 Agent
```
Prüfe zuerst die aktuelle Gemini-Dokumentation (SDK, Funktionsaufrufe, Modellnamen der kostenlosen
Stufe). Implementiere agent/ gemäß Abschnitt 10: LLMProvider, Werkzeuge, Orchestrator mit manueller
Schleife, Trace. Schlüssel nur aus Umgebungsvariablen. Zahlen in Antworten nur aus Werkzeugausgaben
(Test). Negativtests aus Abschnitt 10. Wiederholung mit Wartezeit bei Ratenlimit.
```

### S16 Export und Demo-Modus
```
Implementiere export.py (CSV und XLSX im Input-Schema, ohne das Original zu verändern) und den
Round-Trip-Test auf einer Testkopie. Implementiere agent/demo.py mit drei aufgezeichneten Fällen
(Einzelsendung per Freitext, Bündelung vieler Sendungen, Bahnfall) und schreibe docs/Demo_Skript.md.
```

### S17 Dokumentation und Prompt-Log
```
Schreibe README (Start in unter 10 Minuten), docs/Annahmen.md (Parameter mit Quelle, Systemgrenze,
Verifikationsstatus), THIRD_PARTY.md final und docs/prompt_log.md (Werkzeuge, wesentliche Prompts,
Ergebnisse, Prüfung durch die Gruppe, kritische Reflexion der KI-Nutzung). Markiere unsichere
Quellen ausdrücklich.
```

### S18 Unabhängiger Review (ohne Codeänderung)
```
Prüfe das Repository ohne Änderungen: alle Gates, Abweichungen zu expected.json und Snapshot,
Zeilenvergleich, Round Trip, Kontrast, Platzhalter, Agent-Negativtests, README auf frischem Rechner,
Attributionen, Secrets im Verlauf (git log -p auf Schlüsselmuster). Gib ein Prüfprotokoll
(bestanden/nicht bestanden, Abweichungen) aus.
```

### S19 Optional (Could): Straßengeometrie als Darstellung
```
Nur nach Freigabe. Erzeuge einmalig Straßengeometrien für die Relationen der Routen-Tabelle über
einen Routing-Dienst, speichere sie als GeoJSON mit Dienst, Profil, Datum und Lizenzhinweis.
Zeige sie als umschaltbare Darstellung mit dem Hinweis "Darstellung, nicht Berechnungsgrundlage".
Der Rechenkern bleibt unverändert; Tests aus G5 müssen unverändert grün bleiben.
```

---

## 14. Live-Demo (45 Minuten Präsentation, davon 12 bis 15 Minuten Demo)

| Schritt | Aktion | Belegt |
|---|---|---|
| 1 | Ist-Karte und Kennzahlen (Einzelversand, 2.266 Sendungen) | Qualität der Rechnung |
| 2 | Wechsel auf M2: Touren, Bündelung, Delta | Funktionsfähigkeit |
| 3 | Wechsel auf M3: Bahnsendungen, Servicegrad 75,68 %, Zielkonflikt | Einordnung |
| 4 | Neue Sendungen einfügen (Freitext über den Agenten), Ergebnis je Sendung | Funktionsfähigkeit |
| 5 | Parameter ändern (A01, A05, A08), Sofortberechnung | Nachvollziehbarkeit |
| 6 | "Wie berechnet?" und Agent-Spur zu einer Sendung | Nachvollziehbarkeit |
| 7 | Prüfungen, Referenzabgleich gegen Excel, Export und eine Zahl in Excel nachrechnen | Qualität der Rechnung |
| 8 | Fehlende Pflichtangabe: Agent verweigert Schätzung | Verlässlichkeit |

Rückfall: Demo-Modus, Bildschirmvideo, lokaler Start ohne Internet (Knoten-Kanten-Ansicht).

---

## 15. Zeitplan (Kalenderwochen 2026/27)

| KW | Zeitraum | Inhalt | Termin |
|---|---|---|---|
| 43 | 19.10. bis 25.10. | S0 bis S3 | |
| 44 | 26.10. bis 01.11. | S4 bis S7 | |
| 45 | 02.11. bis 08.11. | S8 bis S10, Folien Zwischenpräsentation | |
| 46 | 09.11. bis 15.11. | S11, S12 (Theme); Zwischenpräsentation | **11.11. Zwischenpräsentation** |
| 47 | 16.11. bis 22.11. | S13 | |
| 48 | 23.11. bis 29.11. | S14 (Spike, Karte) | |
| 49 | 30.11. bis 06.12. | S15 | |
| 50 | 07.12. bis 13.12. | S16, Demo-Skript | |
| 51 | 14.12. bis 20.12. | S17, Seminararbeit | |
| 52 | 21.12. bis 27.12. | S18, Fehlerbehebung, Freeze | |
| 53 | 28.12. bis 03.01. | Proben, Release-Tag, Abgabepaket | |
| 1 | ab 04.01. | | **04.01. Abgabe (Olat, bis 20 Uhr); 06.01. Abschlusspräsentation** |

Für die Zwischenpräsentation (11.11.) reichen: Excel-Ergebnisse, Architektur, Kern bis G5 (teilweise), Theme-Vorschau.

---

## 16. Risiken und offene Punkte

| Punkt | Risiko | Maßnahme |
|---|---|---|
| Emissionsfaktoren (P4) | Quelle und Systemgrenze nicht abschließend belegt | Abgleich mit GLEC / ISO 14083, `verified`-Flag sichtbar |
| Straßenkilometer (P5) | Luftlinie × 1,22 ist eine Näherung | als Annahme ausweisen, Sensitivität zeigen |
| Gespeicherte Excel-Werte | stammen aus einer Berechnungsengine, ggf. nicht Excel | in Microsoft Excel neu berechnen, Referenz neu erzeugen |
| Rundung | abweichende Rangfolge | `round_half_away`, Test |
| openpyxl | Verlust von Diagrammen beim Speichern | nur Testkopien beschreiben |
| NiceGUI | Karte oder Linienmuster nicht umsetzbar | Spike S14, Rückfall FastAPI plus Leaflet |
| OSM-Kacheln | Nutzungsrichtlinie, Netzausfall | Attribution, SVG-Rückfall, optional PMTiles |
| Gemini kostenlos | Limits, Datenschutz, Bedingungen | Demo-Modus, nur lokale Demo, nur synthetische Daten |
| Datenfreigabe | Seminardaten im GitHub-Repo | privat; Freigabe klären, sonst nur lokal |
| Rollen der Gruppe | Zuständigkeit unklar | vor KW 44 festlegen |
| Kostengleichheit M2 und M3 | Rückfrage in der Präsentation | Erklärung vorbereiten |
| Tests T01 bis T10 | Nummerierung dieses Dokuments nicht maßgeblich | Excel-Definition lesen (S3) |

## 17. Definition of Done

1. Alle Gates G0 bis G8 bestanden.
2. Kennzahlen und alle 2.266 Sendungen innerhalb 1e-9 zur Excel, Snapshot innerhalb 1e-8.
3. Jede Kennzahl mit Formel, Parameter, Quelle im Erklärungspanel.
4. Keine Platzhaltertexte, Kontrasttest bestanden, Attributionen sichtbar.
5. Agent erfindet in den Negativtests keine Zahl.
6. README: Start auf frischem Rechner in unter 10 Minuten.
7. Demo-Modus, Video und lokaler Start getestet.
8. Prompt-Log vollständig, kritische Reflexion der KI-Nutzung in Arbeit und Präsentation.
9. Release-Tag `v1.0-abgabe`, Abgabepaket in Olat vor dem 04.01.2027, 20 Uhr.

---

## Zusammenfassung

| Aspekt | Kernaussage |
|---|---|
| Referenz | Excel v11; Python ist ein Port, Abnahme 1e-9 (Snapshot 1e-8) |
| Szenarien | Ist, M2 (Next-Fit), M3 (Bahn, dann Bündelung) |
| Zielwerte | Ist 306.924,11 kg; M2 −16,89 %; M3 −53,31 %; Kosten −24,95 %; Servicegrad M3 75,68 % |
| Karte | Luftlinien aus `Routen`, OSM-Kacheln gedämpft, Attribution, SVG-Rückfall; Routing nur optional als Darstellung |
| Design | heller Modus, eine Akzentfarbe, Tokens mit berechneten Kontrasten, keine Dekoration |
| GitHub | privates Repo, geschützter `main`, PR mit Review, CI (ruff, mypy, pytest), Secrets nur lokal |
| Prompts | Start, S0 bis S19 mit Gates G0 bis G8 |
| Zeitplan | KW 43 bis KW 1; 11.11. Zwischenpräsentation, 04.01. Abgabe, 06.01. Präsentation |
| Offen | Faktoren P4, Straßenkilometer P5, Excel-Neuberechnung, Datenfreigabe, Rollen |
