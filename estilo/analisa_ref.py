"""Frame-by-frame analysis of ONE reference video (OpenCV, local, read-only).

Measures, per frame: luma, saturation, contrast, edge density, frame difference, histogram jump,
optical flow (global pan dx/dy, zoom, rotation, motion energy) and audio energy. From that it derives
cut points, shot lengths and a colour palette. It describes what happens on screen; it does not judge.

Usage: python estilo/analisa_ref.py VIDEO OUT_DIR
Writes: metricas.csv, resumo.json, folha_cortes.png (frames around cuts), folha_tempo.png (even sampling)
Env: FFMPEG / FFPROBE (default: found on PATH)
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys

import cv2
import numpy as np

FFMPEG = os.environ.get("FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"
FFPROBE = os.environ.get("FFPROBE") or shutil.which("ffprobe") or "ffprobe"
SW = 160  # analysis width: enough for global camera motion


def probe(path: str) -> dict:
    out = subprocess.run(
        [FFPROBE, "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return json.loads(out)


def audio_envelope(path: str, fps: float):
    """RMS energy of the audio per video frame (None if there is no audio)."""
    raw = subprocess.run(
        [FFMPEG, "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
        capture_output=True,
    ).stdout
    if not raw:
        return None
    a = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    hop = int(16000 / fps)
    n = len(a) // hop
    if n == 0:
        return None
    return np.sqrt((a[: n * hop].reshape(n, hop) ** 2).mean(1))


def palette(frames, k: int = 5):
    px = np.concatenate([cv2.resize(f, (48, 48)).reshape(-1, 3) for f in frames]).astype(np.float32)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    _, labels, centers = cv2.kmeans(px, k, None, crit, 3, cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(labels.flatten(), minlength=k)
    order = np.argsort(-counts)
    return [
        (
            "#%02X%02X%02X" % (int(centers[i][2]), int(centers[i][1]), int(centers[i][0])),
            round(float(counts[i] / counts.sum()), 3),
        )
        for i in order
    ]


def measure(video: str):
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    sh = max(2, int(h * SW / w))
    ys, xs = np.mgrid[0:sh, 0:SW]
    rx, ry = xs - SW / 2, ys - sh / 2
    rn = np.sqrt(rx**2 + ry**2) + 1e-6
    rows, prev_g, prev_hist, i = [], None, None, 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        small = cv2.resize(frame, (SW, sh))
        g = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [16, 8], [0, 180, 0, 256])
        cv2.normalize(hist, hist)
        edges = cv2.Canny(g, 80, 160)
        row = dict(
            q=i,
            t=round(i / fps, 4),
            luma=float(g.mean()),
            sat=float(hsv[..., 1].mean()),
            contraste=float(g.std()),
            bordas=float((edges > 0).mean()),
            dif=0.0,
            histd=0.0,
            dx=0.0,
            dy=0.0,
            zoom=0.0,
            giro=0.0,
            fluxo=0.0,
        )
        if prev_g is not None:
            row["dif"] = float(np.abs(g.astype(np.int16) - prev_g.astype(np.int16)).mean())
            row["histd"] = float(cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA))
            flow = cv2.calcOpticalFlowFarneback(prev_g, g, None, 0.5, 2, 15, 2, 5, 1.1, 0)
            fx, fy = flow[..., 0], flow[..., 1]
            row["dx"], row["dy"] = float(fx.mean()), float(fy.mean())
            row["zoom"] = float(((fx * rx + fy * ry) / rn).mean())  # > 0 expands (zoom in)
            row["giro"] = float(((fy * rx - fx * ry) / rn).mean())  # rotation
            row["fluxo"] = float(np.sqrt(fx**2 + fy**2).mean())
        rows.append(row)
        prev_g, prev_hist, i = g, hist, i + 1
    cap.release()
    return rows, fps, w, h


def detect_cuts(rows):
    histd = np.array([r["histd"] for r in rows])
    thr = max(0.35, np.median(histd) + 6 * (np.median(np.abs(histd - np.median(histd))) + 1e-6))
    cuts = [r["q"] for r in rows if r["q"] > 0 and r["histd"] > thr and r["dif"] > 8]
    merged: list[int] = []
    for c in cuts:  # drop cuts closer than 3 frames
        if not merged or c - merged[-1] > 3:
            merged.append(c)
    return merged


def sheet(frames: dict, picks: list[int], fps: float, w: int, h: int, path: str, cols: int = 6) -> None:
    tw = 240
    th = int(tw * h / w)
    rows_img = []
    for k in range(0, len(picks), cols):
        tiles = []
        for q in picks[k : k + cols]:
            if q in frames:
                tile = cv2.resize(frames[q], (tw, th))
                cv2.putText(tile, f"q{q} {q / fps:.2f}s", (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 255), 1, cv2.LINE_AA)
                tiles.append(tile)
        while len(tiles) < cols:
            tiles.append(np.zeros((th, tw, 3), np.uint8))
        rows_img.append(np.hstack(tiles))
    cv2.imwrite(path, np.vstack(rows_img))


def main(video: str, outdir: str) -> None:
    os.makedirs(outdir, exist_ok=True)
    info = probe(video)
    vstream = next(s for s in info["streams"] if s["codec_type"] == "video")
    has_audio = any(s["codec_type"] == "audio" for s in info["streams"])
    rows, fps, w, h = measure(video)
    n = len(rows)
    if n == 0:
        with open(os.path.join(outdir, "resumo.json"), "w", encoding="utf-8") as fh:
            json.dump({"erro": "sem quadros"}, fh)
        return
    cuts = detect_cuts(rows)
    env = audio_envelope(video, fps) if has_audio else None
    if env is not None:
        for r in rows:
            r["audio"] = float(env[r["q"]]) if r["q"] < len(env) else 0.0
    with open(os.path.join(outdir, "metricas.csv"), "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    wanted = sorted({0, n - 1, *cuts, *[c - 1 for c in cuts if c > 0]})
    if len(wanted) > 24:
        wanted = [wanted[j] for j in np.linspace(0, len(wanted) - 1, 24).astype(int)]
    uniform = [int(x) for x in np.linspace(0, n - 1, 24)]
    need = set(wanted) | set(uniform)
    got, cap, i = {}, cv2.VideoCapture(video), 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if i in need:
            got[i] = frame
        i += 1
    cap.release()
    sheet(got, wanted, fps, w, h, os.path.join(outdir, "folha_cortes.png"))
    sheet(got, uniform, fps, w, h, os.path.join(outdir, "folha_tempo.png"))

    flow = np.array([r["fluxo"] for r in rows])
    seg = np.diff([0] + cuts + [n])
    third = n // 3 or 1
    summary = dict(
        arquivo=os.path.basename(video),
        largura=w,
        altura=h,
        fps=round(fps, 3),
        quadros=n,
        duracao_s=round(n / fps, 3),
        proporcao=round(w / h, 3),
        tem_audio=has_audio,
        n_cortes=len(cuts),
        cortes_t=[round(c / fps, 3) for c in cuts],
        duracao_media_plano_s=round(float(seg.mean() / fps), 3),
        plano_min_s=round(float(seg.min() / fps), 3),
        plano_max_s=round(float(seg.max() / fps), 3),
        fluxo_medio=round(float(flow.mean()), 4),
        fluxo_p95=round(float(np.percentile(flow, 95)), 4),
        zoom_medio=round(float(np.mean([r["zoom"] for r in rows])), 4),
        giro_abs_medio=round(float(np.mean([abs(r["giro"]) for r in rows])), 4),
        luma_medio=round(float(np.mean([r["luma"] for r in rows])), 1),
        sat_media=round(float(np.mean([r["sat"] for r in rows])), 1),
        contraste_medio=round(float(np.mean([r["contraste"] for r in rows])), 1),
        bordas_media=round(float(np.mean([r["bordas"] for r in rows])), 4),
        paleta=palette([got[q] for q in uniform if q in got]),
        fluxo_terco1=round(float(flow[:third].mean()), 4),
        fluxo_terco2=round(float(flow[third : 2 * third].mean()), 4),
        fluxo_terco3=round(float(flow[2 * third :].mean()), 4),
        codec=vstream.get("codec_name"),
    )
    with open(os.path.join(outdir, "resumo.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1)
    print(os.path.basename(video), w, h, round(fps, 1), n, "frames,", len(cuts), "cuts")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
