"""Funnel step 5: the suggestion table (time | speech | signals | description | text | reference | confidence).

The table is the single human approval point: nothing is edited until a person reads it.
The "reference" column comes from an optional haiku_v01.json produced by a small LLM that looked
at the key frames: {"c028": {"referencia": "...", "confianca": "media"}}.

Usage: python cacador/05_tabela.py WORK_DIR
Reads:  candidatos_vNN.csv (highest NN), florence_v01.json, haiku_v01.json (optional)
Writes: tabela_cacador_vNN.md
"""

from __future__ import annotations

import csv
import glob
import json
import os
import re
import sys

from common import mmss, next_version


def latest(work: str, stem: str, ext: str) -> str:
    files = glob.glob(os.path.join(work, f"{stem}_v*.{ext}"))
    if not files:
        sys.exit(f"no {stem}_vNN.{ext} in {work}")
    return max(files, key=lambda p: int(re.search(r"_v(\d+)\.", p).group(1)))


def main(work: str) -> None:
    with open(latest(work, "candidatos", "csv"), encoding="utf-8") as fh:
        cands = list(csv.DictReader(fh))
    with open(os.path.join(work, "florence_v01.json"), encoding="utf-8") as fh:
        florence = json.load(fh)
    haiku_path = os.path.join(work, "haiku_v01.json")
    haiku = {}
    if os.path.exists(haiku_path):
        with open(haiku_path, encoding="utf-8") as fh:
            haiku = json.load(fh)
    lines = [
        "| id | tempo | fala | sinais | descrição (Florence-2) | texto lido | referência (LLM) | conf. |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(cands, key=lambda r: float(r["t_quadro"])):
        key = r["quadro"].replace("\\", "/")
        fl = florence.get(key) or next((v for k, v in florence.items() if k.endswith(os.path.basename(key))), {})
        hh = haiku.get("c%03d" % int(r["id"]), {})
        lines.append(
            f"| c{int(r['id']):03d} | {mmss(float(r['t_quadro']))} | {r['fala'][:80]} | {r['sinais']} "
            f"| {fl.get('descricao', '')[:110]} | {fl.get('texto', '').strip()[:30]} "
            f"| {hh.get('referencia', '')} | {hh.get('confianca', '')} |"
        )
    out = next_version(work, "tabela_cacador", "md")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("ok", len(cands), "rows ->", out.name)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
