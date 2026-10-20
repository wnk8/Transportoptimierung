# Annahmen, Quellen, Systemgrenze und Verifikation

Stand: 20.10.2026. Quelle aller Werte: Blatt Assumptions der Excel v11 (`Thema1_Transportkonzept_v11_Beispieldaten.xlsx`). Die App liest die Werte zur Laufzeit aus der Mappe; diese Tabelle ist eine Abschrift zum Nachlesen. Bei Abweichung gilt die Mappe.

Markierung der Belege:

- **unbelegt**: "Eigene Annahme" ohne Quelle (Setzung der Gruppe). Vor Abgabe begründen oder belegen.
- **Sekundärquelle**: extern belegt, Primärverifikation ausstehend.
- **belegt**: extern belegt und unkritisch.

## 1. Steuerparameter (Assumptions A)

| ID | Parameter | Wert | Einheit | Beleg | Quelle laut Assumptions |
|---|---|---:|---|---|---|
| A01 | Bahn-Mindestdistanz | 500 | km | **unbelegt** | Keine Quelle. Beleg aus der Literatur zum Kombinierten Verkehr ist offen. |
| A02 | Lkw-Vor- und Nachlauf je Bahnverlagerung (gesamt) | 100 | km | **unbelegt** | Pauschale der Gruppe. |
| A03 | Fahrzeug für Vor- und Nachlauf | Lkw 7,5t | Auswahl | **unbelegt** | Faktor siehe B3. |
| A04 | Bahn-Traktion | elektrisch | Auswahl | **unbelegt** | Elektrisch als Standardfall im Kombinierten Verkehr der EU, Diesel als ungünstiger Fall. |
| A05 | Zusatzlaufzeit der Bahn | 1 | Tage | **unbelegt** | Keine Quelle, keine Fahrplandaten. |
| A06 | Zulässige Verspätung | 2 | Tage | **unbelegt** | Setzung zur Vorgabe "keine unvertretbare Verschlechterung des Servicegrads". |
| A07 | Bahn-Kostenaufschlag | 0 | Anteil | **unbelegt** | Kein Bahntarif. Vorsichtige Setzung; in Original_Data war die Bahn je tkm günstiger. |
| A08 | Zulässige Kostensteigerung je Maßnahme | 0,1 | Anteil | **unbelegt** | Setzung der Gruppe. |
| A09 | Schwelle schlecht ausgelasteter Touren | 0,5 | Anteil | **unbelegt** | Setzung der Gruppe. |
| A10 | Umweg-Zuschlag je zusätzlichem Stopp | 0,2 | Anteil | **unbelegt** | Setzung der Gruppe, im Seminar zu begründen. |
| A11 | Lastunabhängiger Verbrauchsanteil α | 1 | Anteil | **unbelegt** | Quelle fehlt; α = 1 vermeidet eine unbelegte Lastkurve. |
| A12 | Emissionsfaktor Diesel (WTW) | 4,19 | kg CO₂e/kg Diesel | **unbelegt** | Aus der Vorgängerdatei übernommen, Primärbeleg offen (P4). |
| A13 | Dichte Diesel | 0,83 | kg/l | **unbelegt** | Aus der Vorgängerdatei übernommen. |
| A14 | Standardwert kg je Palette | 268 | kg/Palette | abgeleitet | Σ Gewicht / Σ Paletten in Original_Data = 268,1. |

## 2. Fahrzeuge und Faktoren (Assumptions B und C2)

| ID | Fahrzeug | Paletten | Nutzlast kg | Verbrauch l/km | GLEC g CO₂e/tkm | Kostensatz €/km | Referenzauslastung |
|---|---|---:|---:|---:|---:|---:|---:|
| B1.1 | Sprinter (3,5t) | 8 | 1.200 | 0,105 | 840 | 1,58 | 0,50 |
| B1.2 | Lkw 7,5t | 16 | 3.000 | 0,175 | 335 | 2,02 | 0,52 |
| B1.3 | Lkw 12t | 24 | 6.000 | 0,210 | 223 | 2,14 | 0,44 |
| B1.4 | Sattelzug 40t | 34 | 24.000 | 0,325 | 101 | 2,24 | 0,16 |

| Größe | Beleg |
|---|---|
| Kapazitäten (B1) | abgeleitet aus Original_Data (Tourdaten je Fahrzeugtyp) |
| Verbrauch (B2) | **unbelegt**: Annahme aus der Vorgängerdatei, vor Abgabe belegen (P4) |
| GLEC-Intensitäten (B3.1 bis B3.4) | **Sekundärquelle**: GLEC Framework v3.2 über GreenCalculus (abgerufen 14.10.2026), Primärverifikation ausstehend |
| Bahn elektrisch 10,8 und Diesel 30,7 g CO₂e/tkm (B3.5, B3.6) | **Sekundärquelle**: GLEC Framework v3.2, wie oben |
| Kostensätze, Referenzauslastung (C2) | abgeleitet aus Original_Data, änderbare Standardwerte |

Hinweis zum Gesamtpaket, Abschnitt 2.4: Dort steht "Bahnfaktor (aktiv, Traktion Diesel) 10,8 g/tkm". Laut Assumptions ist 10,8 g/tkm der Wert für elektrische Traktion (A04 = elektrisch); Diesel hat 30,7 g/tkm. Die App folgt der Excel.

## 3. Orts- und Distanzlogik (Assumptions I)

| ID | Parameter | Wert | Einheit | Beleg | Quelle |
|---|---|---:|---|---|---|
| I01 | Straßenfaktor auf Luftlinie | 1,22 | Faktor | **unbelegt** (eigene Auswertung) | Median Entfernung/Luftlinie über 45 Relationen in Original_Data; Definition der Entfernung im Datensatz offen |
| I02 | Streuungsgrenze für Ortsnamen ohne PLZ | 25 | km | **unbelegt** | Setzung der Gruppe nach Auswertung der GeoNames-Daten |
| I03 | Mittlerer Erdradius | 6.371,0088 | km | belegt | IUGG, WGS84 |

## 4. Abgeleitete Größen (Assumptions C1)

| ID | Formel | Wert (Beispieldaten) |
|---|---|---:|
| C01 | aktiver Bahnfaktor nach A04 | 10,8 g CO₂e/tkm |
| C02 | GLEC-Intensität des Fahrzeugs A03 | 335 g CO₂e/tkm |
| C03 | $A_{05} \le A_{06}$ | 1 |
| C04 | $\sum Fr_i / \sum K_i^{\mathrm{Modell}}$ über gültige Zeilen mit Fracht | 0,646527 |
| C05 | Anzahl gültiger Sendungen | 2.266 |

## 5. Rechenweg (Formelregister K2)

Distanz:

$$d = \begin{cases} d^{\mathrm{Eingabe}} & \text{falls angegeben}\\ d^{\mathrm{Relation}} & \text{falls vorhanden}\\ I_{01}\cdot 2R\arcsin\sqrt{\sin^2\frac{\Delta\varphi}{2}+\cos\varphi_1\cos\varphi_2\sin^2\frac{\Delta\lambda}{2}} & \text{sonst}\end{cases}$$

Fahrzeug und Auslastung:

$$p = \max\left(1, \left\lceil \frac{kg}{A_{14}} \right\rceil\right),\quad n = \max\left(1, \left\lceil\frac{p}{p_{\max}}\right\rceil, \left\lceil\frac{kg}{kg_{\max}}\right\rceil\right),\quad u = \max\left(\frac{kg}{n\,kg_r}, \frac{p}{n\,p_r}\right)$$

CO₂e Hauptrechnung (Fahrzeug-km) und Kontrollrechnung (tkm):

$$E = d\,n\cdot A_{12} A_{13} l_r \cdot\left(\alpha + (1-\alpha)\frac{kg/(n\,kg_r)}{u_{\mathrm{ref},r}}\right),\qquad E_{tkm} = \frac{kg}{1000}\,d\cdot g_r/1000$$

Bahn:

$$\mathrm{Bahn} \Leftrightarrow d > A_{01} \wedge A_{05}\le A_{06} \wedge K(1+A_{07}) \le K(1+A_{08}),\qquad E_B = \frac{\frac{kg}{1000}\min(d,A_{02})\,C_{02} + \frac{kg}{1000}(d-\min(d,A_{02}))\,C_{01}}{1000}$$

Tour (Next-Fit je Tag und Startort, Rang nach Entfernung absteigend):

$$km_T = d_{\max}\,(1 + A_{10}(\mathrm{Stopps}-1)),\qquad \text{bündeln} \Leftrightarrow n_T\ge 2 \wedge u_{\min} < A_{09} \wedge E_T < \sum E_i \wedge K_T \le \sum K_i (1+A_{08})$$

Zuordnung auf Sendungen und Kennzahlen:

$$x_i = \frac{tkm_i}{\sum_{j\in T} tkm_j}X_T,\qquad \Delta = \frac{\sum \mathrm{Plan}}{\sum \mathrm{Ist}} - 1,\qquad S = 1 - \frac{N_{\mathrm{Bahn}}}{N}\ (A_{05}>0)$$

Rundung vor dem Ranking: 6 Nachkommastellen, kaufmännisch (half away from zero) über `decimal.Decimal`.

## 6. Straßenrouten (Darstellung und Variante)

Straßenrouten kommen von OpenRouteService (Profil `driving-hgv`, Lkw-Beschränkungen laut ORS) und werden lokal gespeichert. Sie sind **nicht** Rechengrundlage des Standards; die Rechnung bleibt Luftlinie mal I01 wie in der Excel.

- Ansicht "Straße gegen Luftlinie": je Relation Luftlinie, Näherung $d_L \cdot I_{01}$, Straßen-km und Faktor $d_S / d_L$; dazu der empirische Faktor $\sum d_S / \sum d_L$ als Prüfwert für I01 (Projektpunkt P5).
- Variante "Distanz aus Straßenrouten": Die Straßen-km gehen als Einträge der Relationstabelle (PLZ_Orte R:T, Input X) in die Rechnung; Quelle je Sendung "Relationstabelle". Die Referenzwerte der Excel gelten dann nicht; mit dem Export "Relationstabelle" rechnet die Excel dieselbe Variante.
- Tourrouten: Das Modell kennt keine Stoppreihenfolge (Tourstrecke $d_{\max}(1 + A_{10}(\text{Stopps}-1))$). Die Karte ordnet die Stopps nach "nächster Nachbar" ab Start; das ist Darstellung.
- Fahrzeugvergleich: Die Tabellen "Warum dieses Fahrzeug?" rechnen alle Fahrzeugklassen mit den Formeln K2.4 bis K2.10. Gewählt ist immer die Klasse der Excel (Rangregel); die übrigen Zeilen sind Vergleichsrechnungen. Einen Pkw enthält die Flotte nicht.

## 7. Systemgrenze

| Bereich | Enthalten | Nicht enthalten |
|---|---|---|
| Emissionen | Well-to-Wheel, Hauptlauf; Bahn mit Vor- und Nachlauf pauschal A02 | Umschlag, Lager, Leerfahrten außerhalb der Faktoren, Infrastruktur |
| Distanz | Luftlinie der PLZ-Schwerpunkte mal I01 oder eingegebene km | Routing, Maut, Verkehr |
| Kosten | Frachtkosten je Sendung (Eingabe oder Modell mal C04), Bahn mit A07 | Umschlags- und Terminalkosten, Bahntarif |
| Servicegrad | Anteil der Sendungen ohne Zusatzlaufzeit | Fahrpläne, Zeitfenster |
| Szenarien | Ist (Einzelversand), M2 (Bündelung der Lkw-Sendungen, Bahn-Sendungen im Ist), M3 (Bahn, dann Bündelung) | Eigenständige Tourbildung ohne Bahnprüfung |

## 8. Verifikationsstatus

| Prüfung | Ergebnis | Nachweis |
|---|---|---|
| Kennzahlen Ist, M2, M3 gegen Excel | höchstens 4e-14 relativ (Abnahme 1e-9) | `tests/core/test_kpis.py` |
| 2.266 Sendungen, Spalten I bis BK | keine Abweichung über 1e-13 | `tests/core/test_columns.py` |
| Blatt Touren (1.715 Zeilen, 428 Touren) und Routen (45 Relationen) | keine Abweichung | `tests/core/test_tours_routes.py` |
| Sensitivität, 14 Zeilen | höchstens 1,6e-10 absolut (Abnahme 1e-8) | `tests/core/test_kpis.py` |
| 20 Prüfungen und Gesamtstatus | wie Excel | `tests/core/test_kpis.py` |
| Gespeicherte Werte der Excel | stammen aus LibreOffice (Assumptions K6.6), nicht aus Microsoft Excel | offen: Neuberechnung in Microsoft Excel und erneut `make reference` |
| Emissionsfaktoren | Sekundärquelle bzw. unbelegt (P4) | offen |
| Straßenfaktor I01 | Näherung (P5), Sensitivität 1,10 und 1,35 in Overview Abschnitt 6 | offen |
