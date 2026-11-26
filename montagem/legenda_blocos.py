"""Turn per-word timings (step 3 output) into SHORT caption blocks, ready for a title/Text+ track.

Reads and writes files only. Blocks are short and editable (CapCut-style): 1-3 words for vertical
video (--max 3), up to ~6 for 16:9. One keyword per block is flagged as a CANDIDATE and
upper-cased as a test; a human always reviews the text before anything is used.

Usage: python montagem/legenda_blocos.py palavras_v01.json OUT_DIR [--max 3] [--pausa 0.35] [--sem-maiuscula]
Output: OUT_DIR/legenda_blocos_vNN.csv and .json (never overwritten)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "cacador"))
from common import next_version  # noqa: E402

# Portuguese function words that should never be picked as the keyword. Edit for other languages.
STOP = set(
    "a o as os um uma uns umas de do da dos das em no na nos nas por para com sem e ou mas que se eu tu ele ela "
    "nós vocês eles elas me te lhe meu minha teu tua seu sua isso isto aquilo esse essa este esta aqui ali lá já só "
    "tá né aí então tipo pra pro tô é foi ser são era vai vou vamos tem tinha ter".split()
)


def clean(word: str) -> str:
    return re.sub(r"[^\w'-]", "", word, flags=re.U)


def keyword_index(words: list[str]) -> int | None:
    """Candidate: the longest non-stop word (>= 4 letters); ties go to the last one."""
    cand = [(len(clean(w)), i) for i, w in enumerate(words) if clean(w).lower() not in STOP and len(clean(w)) >= 4]
    return max(cand, key=lambda x: (x[0], x[1]))[1] if cand else None


def make_blocks(words: list[dict], mx: int, pause: float) -> list[list[dict]]:
    out, cur = [], []
    for w in words:
        if w.get("t0") is None or w.get("t1") is None:
            continue
        if cur:
            gap = w["t0"] - cur[-1]["t1"]
            sentence_end = re.search(r"[.!?…]$", cur[-1]["w"].strip())
            if len(cur) >= mx or gap > pause or sentence_end:
                out.append(cur)
                cur = []
        cur.append(w)
    if cur:
        out.append(cur)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("palavras")
    ap.add_argument("saida")
    ap.add_argument("--max", type=int, default=3)
    ap.add_argument("--pausa", type=float, default=0.35)
    ap.add_argument("--sem-maiuscula", action="store_true")
    a = ap.parse_args()
    with open(a.palavras, encoding="utf-8") as fh:
        segs = json.load(fh)
    words = [p for s in segs for p in s.get("palavras", [])]
    rows = []
    for i, block in enumerate(make_blocks(words, a.max, a.pausa), 1):
        ws = [x["w"].strip() for x in block]
        k = keyword_index(ws)
        shown = list(ws)
        if k is not None and not a.sem_maiuscula:
            shown[k] = shown[k].upper()
        rows.append(
            {
                "id": i,
                "t_ini": round(block[0]["t0"], 3),
                "t_fim": round(block[-1]["t1"], 3),
                "texto": " ".join(shown),
                "palavra_chave": clean(ws[k]) if k is not None else "",
                "revisar": "sim",
            }
        )
    base = next_version(a.saida, "legenda_blocos", "csv").with_suffix("")
    with open(base.with_suffix(".csv"), "x", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "t_ini", "t_fim", "texto", "palavra_chave", "revisar"])
        w.writeheader()
        w.writerows(rows)
    with open(base.with_suffix(".json"), "x", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)
    durations = [r["t_fim"] - r["t_ini"] for r in rows] or [0]
    print(
        f"{len(rows)} blocks (max {a.max} words) from {len(words)} words; mean {sum(durations) / len(durations):.2f}s -> {os.path.basename(base)}.csv"
    )


if __name__ == "__main__":
    main()
