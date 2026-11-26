"""Funnel step 1 (OpenCV): motion, brightness and face size, sampled ~10x per second.

Read-only on the source video. Writes one CSV row per sample.

Usage: python cacador/01_opencv_marcar.py VIDEO OUT.csv
Env:   YUNET_MODEL  path to face_detection_yunet_*.onnx (optional; faces are skipped without it)
"""

from __future__ import annotations

import csv
import os
import sys

import cv2
import numpy as np
from common import env


def build_detector():
    model = env("YUNET_MODEL")
    if not model or not os.path.isfile(model):
        print("aviso/warning: YUNET_MODEL not set or missing; face columns will be 0", file=sys.stderr)
        return None
    return cv2.FaceDetectorYN.create(model, "", (640, 360), 0.6)


def main(video: str, out_csv: str) -> None:
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        sys.exit(f"cannot open {video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, round(fps / 10))  # ~10 samples per second for motion
    detector = build_detector()
    prev = None
    rows = []
    i = 0
    while cap.grab():
        if i % step == 0:
            ok, frame = cap.retrieve()
            if not ok:
                break
            gray = cv2.cvtColor(cv2.resize(frame, (160, 90)), cv2.COLOR_BGR2GRAY).astype(np.float32)
            motion = float(np.abs(gray - prev).mean()) if prev is not None else 0.0
            prev = gray
            faces, area = 0, 0.0
            if detector is not None and i % (step * 5) == 0:  # faces ~2x per second
                _, found = detector.detect(cv2.resize(frame, (640, 360)))
                if found is not None:
                    faces = len(found)
                    area = float(max(f[2] * f[3] for f in found)) / (640 * 360)
            rows.append((round(i / fps, 2), round(motion, 2), round(float(gray.mean()), 1), faces, round(area, 4)))
        i += 1
    cap.release()
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["t", "movimento", "brilho", "rostos", "area_rosto"])
        writer.writerows(rows)
    print(f"ok {len(rows)} samples, {i} frames, {fps:.2f} fps")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
