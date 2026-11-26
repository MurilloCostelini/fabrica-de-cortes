"""Adaptive key frames: keep a frame whenever the content changed enough since the last kept one
(new text, new object, a cut). One contact sheet per video, at most 48 frames.

Usage: python estilo/quadros_chave.py VIDEO OUT_PREFIX [threshold=9.0]
Writes: OUT_PREFIX.jpg (sheet) and OUT_PREFIX.json (timestamps in seconds)
"""

from __future__ import annotations

import json
import sys

import cv2
import numpy as np


def main(video: str, prefix: str, threshold: float = 9.0) -> None:
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w, h = cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    sw = 96
    sh = int(h * sw / w)
    last, keys, i = None, [], 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        g = cv2.cvtColor(cv2.resize(frame, (sw, sh), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.float32)
        if last is None:
            keys.append((i, frame.copy()))
            last = g
        elif float(np.abs(g - last).mean()) > threshold:
            keys.append((i, frame.copy()))
            last = g
        i += 1
    cap.release()
    if not keys:
        sys.exit("no frames read")
    if len(keys) > 48:
        keys = [keys[j] for j in np.linspace(0, len(keys) - 1, 48).astype(int)]
    th = 300
    tw = int(th * w / h)
    cols = 8 if tw < 200 else 6
    tiles = []
    for q, frame in keys:
        tile = cv2.resize(frame, (tw, th), interpolation=cv2.INTER_AREA)
        cv2.putText(tile, f"{q / fps:.2f}s", (3, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
        tiles.append(tile)
    while len(tiles) % cols:
        tiles.append(np.zeros((th, tw, 3), np.uint8))
    rows = [np.hstack(tiles[k : k + cols]) for k in range(0, len(tiles), cols)]
    cv2.imwrite(prefix + ".jpg", np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 86])
    with open(prefix + ".json", "w", encoding="utf-8") as fh:
        json.dump([round(q / fps, 3) for q, _ in keys], fh)
    print(prefix, len(keys), "key frames out of", i)


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) == 4 else 9.0)
