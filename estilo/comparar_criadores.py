"""Compare creators (or videos) by the numbers: one resumo.json per video -> one table.

Run estilo/analisa_ref.py on several videos of each creator, then point this script at the output
folders. It prints a Markdown table (mean of each metric per creator) so editing styles can be
compared side by side: cut rhythm, camera motion, colour, how pace changes through the video.
It shows patterns; deciding which pattern is "the right one" stays with a human.

Usage: python estilo/comparar_criadores.py NAME=DIR [NAME=DIR ...] [--csv out.csv]
  DIR is searched recursively for resumo.json files (every video of that creator).
"""

from __future__ import annotations

import csv
import glob
import json
import os
import statistics
import sys

METRICS = [
    ("duracao_s", "duration (s)"),
    ("duracao_media_plano_s", "avg shot (s)"),
    ("n_cortes", "cuts"),
    ("fluxo_medio", "motion"),
    ("zoom_medio", "zoom drift"),
    ("giro_abs_medio", "rotation"),
    ("luma_medio", "luma"),
    ("sat_media", "saturation"),
    ("contraste_medio", "contrast"),
    ("bordas_media", "edge density"),
]


def load(folder: str) -> list[dict]:
    out = []
    for p in sorted(glob.glob(os.path.join(folder, "**", "resumo.json"), recursive=True)):
        with open(p, encoding="utf-8") as fh:
            data = json.load(fh)
        if "erro" not in data:
            out.append(data)
    return out


def cuts_per_minute(rows: list[dict]) -> float:
    total = sum(r["duracao_s"] for r in rows)
    return round(60 * sum(r["n_cortes"] for r in rows) / total, 2) if total else 0.0


def pace_trend(rows: list[dict]) -> float:
    """Mean ratio of motion in the last third over the first third (> 1 = accelerates)."""
    ratios = [r["fluxo_terco3"] / r["fluxo_terco1"] for r in rows if r.get("fluxo_terco1")]
    return round(statistics.mean(ratios), 2) if ratios else 0.0


def main(argv: list[str]) -> None:
    csv_out = argv[argv.index("--csv") + 1] if "--csv" in argv else None
    pairs = [a for a in argv if "=" in a]
    if not pairs:
        sys.exit(__doc__)
    table = []
    for pair in pairs:
        name, folder = pair.split("=", 1)
        rows = load(folder)
        if not rows:
            print(f"warning: no resumo.json under {folder}", file=sys.stderr)
            continue
        entry = {"creator": name, "videos": len(rows)}
        for key, label in METRICS:
            entry[label] = round(statistics.mean(r[key] for r in rows), 3)
        entry["cuts/min"] = cuts_per_minute(rows)
        entry["pace trend"] = pace_trend(rows)
        table.append(entry)
    if not table:
        sys.exit("nothing to compare")
    headers = list(table[0].keys())
    print("| " + " | ".join(headers) + " |")
    print("|" + "---|" * len(headers))
    for e in table:
        print("| " + " | ".join(str(e[h]) for h in headers) + " |")
    if csv_out:
        with open(csv_out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=headers)
            w.writeheader()
            w.writerows(table)


if __name__ == "__main__":
    main(sys.argv[1:])
