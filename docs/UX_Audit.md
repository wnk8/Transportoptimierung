# UX-Audit vor dem Redesign (Stand 23.10.2026)

Geprüft: `/`, `/ergebnis`, `/info` bei 1024, 1440 und 1920 px. Referenzen: Squarespace „Popular Designs“, Lovable Website-Templates.

## Befunde

| Prio | Befund | Maßnahme |
|---|---|---|
| P1 | Kein Einstieg: Erstbesucher landen direkt im Eingabeformular und sehen nicht, was das Werkzeug leistet. | Landing Page auf `/` mit Nutzen, Kennzahlen der Beispieldaten und zwei klaren Aktionen. Rechnen auf `/rechnen`. |
| P1 | Inhalt auf 1280 px begrenzt: bei 1920 px bleiben rechts und links je rund 320 px leer; Karte und Tabellen wirken eng. | Vollbreite mit festem Rand `clamp(16px, 4vw, 72px)`, nur Fließtext behält eine Lesebreite. |
| P2 | Schwebende Leiste „Berechnen“ verdeckt beim Scrollen Inhalte (Datenbestand, Abschnittsgrenze). | Ab 1100 px sticky Zusammenfassung rechts neben den Eingaben, darunter bleibt die Leiste. |
| P2 | Keine Orientierung im Ablauf: Wo stehe ich, was fehlt noch? | Schrittleiste 1 Sendungen, 2 Parameter, 3 Ergebnis mit Status als Text. |
| P2 | Marke nur als „TK.“, Seite trägt keinen Namen und keine Aussage. | Marke „TK. TourKlima“ mit Claim, Logo bleibt. |
| P2 | „Parameter ändern“ und weitere Hauptaktionen nur als kleine Textlinks. | Sekundäre Pillen-Schaltflächen mit Hover- und Druckzustand. |
| P3 | Footer ist eine einzige graue Zeile, Attribution schwer lesbar. | Mehrspaltiger Footer: Produkt, Methodik, Daten und Attribution. |
| P3 | Info-Seite: fünf Tabs nebeneinander, Inhalt lang. | Seitennavigation links (Dokumentationslayout) ab 1100 px. |
| P3 | Fließtext und Überschriften in gleicher Tinte, Hierarchie nur über Größe. | Feine Abstufung: Überschriften `--text`, Fließtext `--text-soft`, Beschriftungen `--muted`, alle mindestens 4,5 : 1. |

## Übernommene Muster aus den Referenzen

- Kopfzeile über volle Breite mit Wortmarke links, Seitenlinks, Haupt-Aktion als Pille rechts.
- Übergroße Headline mit kurzem Untertitel und zwei Aktionen (primär, sekundär).
- Kennzahlen als ruhige Reihe direkt unter dem Hero.
- Drei nummerierte Schritte „So funktioniert es“.
- Funktionsraster in drei Spalten, jede Spalte mit Titel, zwei Sätzen und Link.
- Abschluss mit großer Aufforderung und mehrspaltigem Footer.

Bewusst nicht übernommen: dunkle Bänder, Vollbildfotos und Verläufe. Die Seite bleibt im hellen White-Mode, Gliederung durch Haarlinien und Raster.
