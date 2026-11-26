"""Generate the SYNTHETIC example clip and sound library used by the demo (no third-party media).

Everything is produced by code: moving shapes, one dark stretch, a flash, tone bursts, a bang and
a silence. That is enough to exercise the OpenCV and audio steps without any copyright question.

Usage: python exemplos/gerar_exemplo.py OUT_DIR      (needs ffmpeg on PATH)
Writes: clip_sintetico.mp4, clip_16k_mono.wav, biblioteca_exemplo/{CATALOGO.csv,sfx/*.wav}
"""

from __future__ import annotations

import csv
import os
import subprocess
import sys
import wave

import cv2
import numpy as np

FPS, W, H, DUR, SR = 25, 640, 360, 30, 16000


def render_frames(path: str) -> None:
    out = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    for i in range(FPS * DUR):
        t = i / FPS
        img = np.full((H, W, 3), (70, 90, 60), np.uint8)
        cv2.circle(img, (int(80 + 40 * t) % W, 180 + int(60 * np.sin(t * 2))), 40, (40, 200, 240), -1)
        cv2.rectangle(img, (400, 100), (520, 220), (200, 80, 80), -1)
        if 8 <= t < 10:  # dark stretch
            img = (img * 0.08).astype(np.uint8)
        if 15 <= t < 15.3:  # flash + sudden motion
            img = np.roll(np.full_like(img, 255), int(300 * (t - 15)), axis=1)
        if 22 <= t < 24:  # large "face-like" block
            cv2.ellipse(img, (320, 180), (150, 170), 0, 0, 360, (150, 190, 230), -1)
        out.write(img)
    out.release()


def audio_signal() -> np.ndarray:
    t = np.arange(SR * DUR) / SR
    y = 0.05 * np.sin(2 * np.pi * 180 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 1.3 * t))  # soft hum
    y[int(3 * SR) : int(4.5 * SR)] = 0  # silence
    y[int(26 * SR) : int(27.5 * SR)] = 0  # silence
    n = int(15.0 * SR)
    y[n : n + 800] += 0.9 * np.random.default_rng(1).standard_normal(800) * np.exp(-np.arange(800) / 150)  # bang
    s = int(22 * SR)
    y[s : s + int(0.5 * SR)] += 0.6 * np.sin(2 * np.pi * 2600 * t[: int(0.5 * SR)])  # loud, high
    return np.clip(y, -1, 1)


def write_wav(path: str, y: np.ndarray, sr: int = SR) -> None:
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((y * 32767).astype("<i2").tobytes())


def main(out: str) -> None:
    os.makedirs(out, exist_ok=True)
    silent = os.path.join(out, "_silent.mp4")
    wav = os.path.join(out, "clip_16k_mono.wav")
    render_frames(silent)
    write_wav(wav, audio_signal())
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            silent,
            "-i",
            wav,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            os.path.join(out, "clip_sintetico.mp4"),
        ],
        check=True,
    )
    os.remove(silent)
    lib = os.path.join(out, "biblioteca_exemplo")
    os.makedirs(os.path.join(lib, "sfx"), exist_ok=True)
    rows = []
    for i, (name, freq) in enumerate([("beep_low", 440), ("beep_mid", 880), ("beep_high", 1760)], 1):
        tt = np.arange(int(0.4 * 48000)) / 48000
        write_wav(os.path.join(lib, "sfx", f"{name}.wav"), 0.5 * np.sin(2 * np.pi * freq * tt) * np.exp(-tt * 6), 48000)
        rows.append({"id": f"SFX{i:03d}", "caminho_relativo": f"sfx/{name}.wav", "descricao": f"synthetic {freq} Hz beep"})
    with open(os.path.join(lib, "CATALOGO.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "caminho_relativo", "descricao"])
        w.writeheader()
        w.writerows(rows)
    print("ok ->", out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
