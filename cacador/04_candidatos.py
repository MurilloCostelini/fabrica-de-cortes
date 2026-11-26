"""Funnel step 4: merge all signals into CANDIDATE moments and extract one frame per candidate.

Signals: sudden motion, dark stretches, big faces, audio events, trigger words in the speech and
(optionally) bursts of quick cuts. Signals closer than GROUP_GAP seconds become one candidate.
The script only MARKS candidates. Choosing what to do with them is the job of a human or an LLM
reading the transcript, and the final table is approved by a human before anything is edited.

Usage: python cacador/04_candidatos.py VIDEO WORK_DIR [cuts.csv]
Reads in WORK_DIR:  opencv_v01.csv, audio_eventos_v01.csv, palavras_v01.json
Writes in WORK_DIR: candidatos_vNN.csv and quadros/*.jpg
cuts.csv (optional) needs a column t_ini_s with the start time of every cut in the edit.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter

import cv2
import numpy as np
from common import next_version

GROUP_GAP = 2.5  # seconds
HERE = os.path.dirname(os.path.abspath(__file__))


def load_triggers(path: str) -> set[str]:
    with open(path, encoding="utf-8") as fh:
        return {line.strip().lower() for line in fh if line.strip() and not line.startswith("#")}


def collect_signals(work: str, cuts_csv: str | None):
    ocv = np.genfromtxt(os.path.join(work, "opencv_v01.csv"), delimiter=",", names=True)
    with open(os.path.join(work, "audio_eventos_v01.csv"), encoding="utf-8") as fh:
        audio = list(csv.DictReader(fh))
    with open(os.path.join(work, "palavras_v01.json"), encoding="utf-8") as fh:
        speech = json.load(fh)
    triggers = load_triggers(os.path.join(HERE, "gatilhos_fala.txt"))

    signals = []  # (t, kind, detail)
    t, motion, bright = ocv["t"], ocv["movimento"], ocv["brilho"]
    face_area = ocv["area_rosto"]
    p_motion = np.percentile(motion, 99.3)
    for i in np.where(motion > p_motion)[0]:
        signals.append((float(t[i]), "movimento_brusco", f"{motion[i]:.1f}"))
    dark = bright < max(np.percentile(bright, 4), 0.3 * np.median(bright))
    i = 0
    while i < len(t):
        if dark[i]:
            j = i
            while j < len(t) and dark[j]:
                j += 1
            if t[j - 1] - t[i] >= 1.0:
                signals.append((float(t[i]), "escuro", f"{t[j - 1] - t[i]:.1f}s"))
            i = j
        else:
            i += 1
    for i in np.where(face_area > 0.06)[0]:
        if i == 0 or face_area[i - 1] <= 0.06:
            signals.append((float(t[i]), "rosto_grande", f"{face_area[i]:.2f}"))
    for row in audio:
        if row["tipo"] in ("silencio", "grito_pico", "pancada", "risada?"):
            signals.append((float(row["t0"]), row["tipo"], row["forca"]))
    for seg in speech:
        for w in seg["palavras"]:
            if w["t0"] is None:
                continue
            word = w["w"].strip(" .,!?").lower()
            if word in triggers:
                signals.append((float(w["t0"]), "gatilho_fala", word))
    if cuts_csv:
        with open(cuts_csv, encoding="utf-8") as fh:
            starts = sorted(float(r["t_ini_s"]) for r in csv.DictReader(fh))
        for a in range(len(starts) - 3):  # 4 cuts in < 3 s = fast rhythm
            if starts[a + 3] - starts[a] < 3.0:
                signals.append((starts[a], "cortes_rapidos", f"{starts[a + 3] - starts[a]:.1f}s"))
    signals.sort()
    return signals, speech


def group(signals):
    groups, current = [], [signals[0]]
    for s in signals[1:]:
        if s[0] - current[-1][0] <= GROUP_GAP:
            current.append(s)
        else:
            groups.append(current)
            current = [s]
    groups.append(current)
    return groups


def main(video: str, work: str, cuts_csv: str | None = None) -> None:
    signals, speech = collect_signals(work, cuts_csv)
    if not signals:
        sys.exit("no signals found; check the input files")
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    os.makedirs(os.path.join(work, "quadros"), exist_ok=True)
    rows = []
    for n, g in enumerate(group(signals), 1):
        t0, t1 = g[0][0], g[-1][0]
        center = (t0 + t1) / 2
        kinds = sorted({x[1] for x in g})
        said = " ".join(s["text"].strip() for s in speech if s["end"] >= t0 - 1.5 and s["start"] <= t1 + 1.5)
        jpg = f"quadros/c{n:03d}_{center:07.2f}.jpg"
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(center * fps))
        ok, frame = cap.read()
        if ok:
            cv2.imwrite(os.path.join(work, jpg), cv2.resize(frame, (640, 360)))
        rows.append(
            {
                "id": n,
                "t0": round(t0, 2),
                "t1": round(t1, 2),
                "t_quadro": round(center, 2),
                "sinais": "+".join(kinds),
                "n_tipos": len(kinds),
                "detalhes": "; ".join(f"{x[1]}={x[2]}" for x in g[:6]),
                "fala": said[:300],
                "quadro": jpg,
            }
        )
    cap.release()
    out = next_version(work, "candidatos", "csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print("ok", len(rows), "candidates; signals:", dict(Counter(x[1] for x in signals)), "->", out.name)


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    main(*sys.argv[1:])
