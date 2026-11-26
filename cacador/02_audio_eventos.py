"""Funnel step 2 (audio): silence, loud/high peaks, bangs and a rough laughter guess.

Input is a 16 kHz mono WAV. The script only MARKS events; it never decides what to do with them.
The "risada?" (laughter) label is a heuristic guess and is named with a question mark on purpose.

Usage: python cacador/02_audio_eventos.py audio_16k_mono.wav OUT.csv
"""

from __future__ import annotations

import csv
import sys
from collections import Counter

import librosa
import numpy as np

HOP = 1600  # 0.1 s at 16 kHz


def runs(mask, minlen):
    """Yield (start, end) index pairs of consecutive True values at least minlen long."""
    out, start = [], None
    for i, m in enumerate(list(mask) + [False]):
        if m and start is None:
            start = i
        if not m and start is not None:
            if i - start >= minlen:
                out.append((start, i))
            start = None
    return out


def detect(y: np.ndarray, sr: int):
    rms = librosa.feature.rms(y=y, frame_length=3200, hop_length=HOP)[0]
    db = 20 * np.log10(rms + 1e-6)
    cen = librosa.feature.spectral_centroid(y=y, sr=sr, n_fft=2048, hop_length=HOP)[0]
    onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP)
    n = min(len(db), len(cen), len(onset))
    db, cen, onset = db[:n], cen[:n], onset[:n]
    t = np.arange(n) * 0.1
    events = []
    p20, p98, p995 = np.percentile(db, 20), np.percentile(db, 98), np.percentile(onset, 99.5)
    for a, b in runs(db < p20 - 3, 12):  # silence >= 1.2 s
        events.append((t[a], t[b - 1] + 0.1, "silencio", round(float((b - a) * 0.1), 1)))
    centroid_median = np.median(cen)
    for a, b in runs((db > p98) & (cen > centroid_median * 1.3), 3):  # loud and high = shout/startle
        events.append((t[a], t[b - 1] + 0.1, "grito_pico", round(float(db[a:b].max()), 1)))
    for i in range(1, n - 1):  # bang: isolated strong onset
        if onset[i] > p995 and onset[i] >= onset[i - 1] and onset[i] >= onset[i + 1]:
            events.append((t[i], t[i] + 0.1, "pancada", round(float(onset[i]), 1)))
    env = np.clip(db - db.mean(), 0, None)  # laughter?: 4-8 Hz energy oscillation over ~1.5 s
    win = 15
    for i in range(0, n - win, 5):
        seg = env[i : i + win]
        if seg.mean() > 3:
            d = np.diff(seg - seg.mean())
            crossings = np.sum(np.diff(np.sign(d)) != 0)
            if crossings >= 6 and seg.std() > 3:
                events.append((t[i], t[i + win - 1], "risada?", round(float(seg.std()), 1)))
    events.sort()
    return events


def main(wav: str, out_csv: str) -> None:
    y, sr = librosa.load(wav, sr=16000, mono=True)
    events = detect(y, sr)
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["t0", "t1", "tipo", "forca"])
        for a, b, kind, strength in events:
            writer.writerow([round(a, 2), round(b, 2), kind, strength])
    print("ok", dict(Counter(e[2] for e in events)))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
