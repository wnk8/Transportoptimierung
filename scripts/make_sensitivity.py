"""Morris-Screening der Beispieldaten rechnen und in data/reference/sensitivity_morris.json speichern.

Aufruf: ``uv run python scripts/make_sensitivity.py [Trajektorien]`` (Standard 20, etwa 15 s).
Die Excel wird nur gelesen.
"""

from __future__ import annotations

import sys
import time

from tk.scenarios import load_model, workbook_shipments
from tk.sensitivity import RESULT_FILE, TARGETS, morris, save
from tk.workbook import load_workbook_data


def main() -> None:
    trajectories = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    data = load_workbook_data()
    start = time.perf_counter()
    screening = morris(load_model(data), workbook_shipments(data), trajectories=trajectories)
    save(screening)
    print(f"{screening.laeufe} Läufe in {time.perf_counter() - start:.1f} s, gespeichert: {RESULT_FILE}")
    for target, label in TARGETS.items():
        top = ", ".join(f"{e.kennung} {e.mu_star:.4f}" for e in screening.effekte[target][:4])
        print(f"{label}: {top}")


if __name__ == "__main__":
    main()
