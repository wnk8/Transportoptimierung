"""Demo-Modus mit aufgezeichneten Abläufen (ohne Sprachmodell, ohne Netz).

Drei vorbereitete Fälle für die Präsentation. Die Werkzeugaufrufe sind fest aufgezeichnet;
die Zahlen im Antworttext werden aus den Werkzeugausgaben eingesetzt, nie im Text
festgeschrieben. Nur die drei aufgezeichneten Anfragen werden abgespielt (wörtlicher Abgleich);
für jede andere Anfrage antwortet der Demo-Modus ohne Zahlen.
"""

from __future__ import annotations

from tk.agent.provider import ScriptedProvider, ToolCall

CASES: dict[str, dict[str, object]] = {
    "einzel": {
        "titel": "Einzelsendung per Freitext",
        "anfrage": "Am 05.05.2025 gehen 800 kg auf 2 Paletten von 70173 Stuttgart nach 20095 Hamburg.",
        "schritte": [
            [
                ToolCall(
                    "parse_shipments",
                    {
                        "sendungen": [
                            {
                                "datum": "05.05.2025",
                                "start": "70173 Stuttgart",
                                "ziel": "20095 Hamburg",
                                "gewicht_kg": 800,
                                "paletten": 2,
                            }
                        ],
                        "ersetzen": True,
                    },
                )
            ],
            [ToolCall("validate_shipments", {})],
            [ToolCall("plan_scenarios", {"mit_bestand": False})],
            "Sendung übernommen ({tool:plan_scenarios:sendungen.0.start} nach {tool:plan_scenarios:sendungen.0.ziel}, "
            "{tool:plan_scenarios:sendungen.0.distanz_km:1} km, Quelle: {tool:plan_scenarios:sendungen.0.distanzquelle}). "
            "Ergebnis: {tool:plan_scenarios:sendungen.0.ergebnis}. CO₂e Ist {tool:plan_scenarios:sendungen.0.co2_ist_kg:1} kg, "
            "Plan {tool:plan_scenarios:sendungen.0.co2_plan_kg:1} kg. Kosten Plan "
            "{tool:plan_scenarios:sendungen.0.kosten_plan_eur:2} €. Servicegrad M3: "
            "{tool:plan_scenarios:kennzahlen.M3.servicegrad:%}.",
        ],
    },
    "buendelung": {
        "titel": "Bündelung vieler Sendungen",
        "anfrage": "Am 03.03.2025 starten in 68159 Mannheim fünf Sendungen nach 55116 Mainz mit 120, 340, 90, 410 "
        "und 260 kg. Lohnt sich eine Sammeltour?",
        "schritte": [
            [
                ToolCall(
                    "parse_shipments",
                    {
                        "sendungen": [
                            {
                                "datum": "03.03.2025",
                                "start": "68159 Mannheim",
                                "ziel": "55116 Mainz",
                                "gewicht_kg": kg,
                            }
                            for kg in (120, 340, 90, 410, 260)
                        ],
                        "ersetzen": True,
                    },
                )
            ],
            [ToolCall("validate_shipments", {})],
            [ToolCall("plan_scenarios", {"mit_bestand": False})],
            "Fünf Sendungen gerechnet. Ergebnis der ersten Sendung: {tool:plan_scenarios:sendungen.0.ergebnis}. "
            "CO₂e Ist {tool:plan_scenarios:kennzahlen.Ist.co2_fzgkm_kg:1} kg, M2 {tool:plan_scenarios:kennzahlen.M2.co2_fzgkm_kg:1} kg. "
            "Kosten Ist {tool:plan_scenarios:kennzahlen.Ist.kosten_eur:2} €, M2 {tool:plan_scenarios:kennzahlen.M2.kosten_eur:2} €. "
            "Gebündelte Touren: {tool:plan_scenarios:touren_gebuendelt}.",
        ],
    },
    "bahn": {
        "titel": "Bahnfall",
        "anfrage": "Am 10.06.2025 fahren 2400 kg von 79098 Freiburg im Breisgau nach 10115 Berlin. Geht das auf die Bahn?",
        "schritte": [
            [
                ToolCall(
                    "parse_shipments",
                    {
                        "sendungen": [
                            {
                                "datum": "10.06.2025",
                                "start": "79098 Freiburg im Breisgau",
                                "ziel": "10115 Berlin",
                                "gewicht_kg": 2400,
                            }
                        ],
                        "ersetzen": True,
                    },
                )
            ],
            [ToolCall("validate_shipments", {})],
            [ToolCall("plan_scenarios", {"mit_bestand": False})],
            [ToolCall("explain_result", {"kennzahl": "bahn"})],
            "Bahn-Entscheidung: {tool:plan_scenarios:sendungen.0.bahn} ({tool:plan_scenarios:sendungen.0.ergebnis}). "
            "Distanz {tool:plan_scenarios:sendungen.0.distanz_km:1} km. CO₂e Ist {tool:plan_scenarios:sendungen.0.co2_ist_kg:1} kg, "
            "Plan {tool:plan_scenarios:sendungen.0.co2_plan_kg:1} kg. Kosten Plan {tool:plan_scenarios:sendungen.0.kosten_plan_eur:2} €. "
            "Servicegrad M3: {tool:plan_scenarios:kennzahlen.M3.servicegrad:%}. Regel: {tool:explain_result:beschreibung}",
        ],
    },
}

NO_CASE = (
    "Demo-Modus: Für diese Anfrage gibt es keinen aufgezeichneten Ablauf. Vorbereitete Fälle: "
    "Einzelsendung, Bündelung, Bahnfall. Für freie Anfragen GEMINI_API_KEY in .env setzen."
)


def match_case(request: str) -> str | None:
    text = request.lower()
    for key, case in CASES.items():
        if str(case["anfrage"]).lower().strip() == text.strip():
            return key
    return None


def demo_provider(request: str) -> ScriptedProvider:
    """Provider für den Demo-Modus; der Fall richtet sich nach der Anfrage."""
    key = match_case(request)
    if key is None:
        return ScriptedProvider([NO_CASE])
    steps = CASES[key]["schritte"]
    assert isinstance(steps, list)
    return ScriptedProvider(steps)
