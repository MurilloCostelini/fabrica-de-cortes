"""Check a timeline against a "before delivering" checklist. READ-ONLY: nothing is fixed.

Input (pick one):
  --json FILE   a dump of the timeline (works without any editor, used by the tests);
  --vivo        read the timeline open in DaVinci Resolve through a scripting bridge
                (set DAVINCI_BRIDGE_DIR to the folder that provides src.utils.resolve_bridge_client;
                 the bridge must be running; NOT covered by automated tests).

JSON format:
  {"nome": "demo", "fps": 24, "trilhas": [
     {"tipo": "video|audio", "n": 1, "clipes": [{"nome": "...", "ini": 0, "fim": 100}]}]}

Rules (each failure becomes one ERRO/AVISO line):
  1 nothing baked: clip names like video_comp_v01, trilha_v02, sfx_v03, *_final, render, *_mix
  2 SFX keep their ORIGINAL name: short audio clips must exist in the catalog (--catalogo) and not look renamed
  3 one music per track: an audio track with 2+ different long clips
  4 SFX overlapping on the same track (they vanish silently in the editor API)
  5 captions: at least one title/Text+ clip is recognised
  6 zoom/layers: counts clips on V2+ (the transform itself is not checked)

Usage: python montagem/conferir_timeline.py --json timeline.json [--catalogo CATALOGO.csv]
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys

BAKED = re.compile(r"(video_comp|trilha_v\d|sfx_v\d|intro_fix|_final|render|_mix)", re.I)
CAPTION = re.compile(r"(text\+|title|titulo|título|legenda|caption|sub)", re.I)
GENERIC_SFX = re.compile(r"^(item_?\d+|sfx_?\d+)$")


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_live() -> dict:  # pragma: no cover - needs a running editor
    bridge = os.environ.get("DAVINCI_BRIDGE_DIR")
    if not bridge:
        sys.exit("set DAVINCI_BRIDGE_DIR to use --vivo")
    os.environ["DAVINCI_RESOLVE_BRIDGE"] = "1"
    sys.path.insert(0, bridge)
    from src.utils.resolve_bridge_client import connect  # type: ignore

    resolve = connect()
    tl = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline()
    out = {"nome": tl.GetName(), "fps": float(tl.GetSetting("timelineFrameRate") or 24), "trilhas": []}
    for kind in ("video", "audio"):
        for n in range(1, int(tl.GetTrackCount(kind)) + 1):
            clips = [
                {"nome": it.GetName(), "ini": it.GetStart(), "fim": it.GetEnd()} for it in (tl.GetItemListInTrack(kind, n) or [])
            ]
            out["trilhas"].append({"tipo": kind, "n": n, "clipes": clips})
    return out


def load_catalog(path: str | None) -> set[str]:
    names: set[str] = set()
    if path and os.path.exists(path):
        with open(path, encoding="utf-8", errors="ignore") as fh:
            for row in csv.reader(fh):
                for cell in row:
                    if re.search(r"\.(wav|mp3|ogg|flac)$", cell, re.I):
                        names.add(os.path.splitext(os.path.basename(cell))[0].lower())
    return names


def check(tl: dict, catalog: set[str]) -> list[tuple[str, str]]:
    msgs: list[tuple[str, str]] = []
    fps = tl["fps"] or 24
    captions = layers = 0
    for track in tl["trilhas"]:
        tag = ("V" if track["tipo"] == "video" else "A") + str(track["n"])
        clips = sorted(track["clipes"], key=lambda c: c["ini"])
        for c in clips:
            if BAKED.search(c["nome"] or ""):
                msgs.append(("ERRO", f"{tag}: '{c['nome']}' looks like a baked piece (rule 1)"))
            if not (c["nome"] or "").strip():
                msgs.append(("AVISO", f"{tag}: unnamed clip at {c['ini']}"))
        if track["tipo"] == "audio":
            short = [c for c in clips if (c["fim"] - c["ini"]) / fps <= 6]
            long_ = [c for c in clips if (c["fim"] - c["ini"]) / fps > 20]
            for c in short:
                base = os.path.splitext(c["nome"] or "")[0].lower()
                if catalog and base not in catalog:
                    msgs.append(("AVISO", f"{tag}: SFX '{c['nome']}' not in the catalog (renamed? rule 2)"))
                if GENERIC_SFX.match(base):
                    msgs.append(("AVISO", f"{tag}: SFX '{c['nome']}' has a generic name, not the original"))
            if len({c["nome"] for c in long_}) >= 2:
                msgs.append(
                    ("AVISO", f"{tag}: {len({c['nome'] for c in long_})} different tracks of music on one track (rule 3)")
                )
            for a, b in zip(clips, clips[1:]):
                if b["ini"] < a["fim"] and (a["fim"] - a["ini"]) / fps <= 6 and (b["fim"] - b["ini"]) / fps <= 6:
                    msgs.append(("ERRO", f"{tag}: SFX '{a['nome']}' and '{b['nome']}' overlap on the same track (rule 4)"))
        else:
            if track["n"] >= 2:
                layers += len(clips)
            captions += sum(1 for c in clips if CAPTION.search(c["nome"] or "") or (c["nome"] and track["n"] >= 3))
    if captions == 0:
        msgs.append(("AVISO", "no caption/Text+ clip recognised (rule 5); check nested timelines"))
    msgs.append(("INFO", f"clips on V2+ (zooms, layers): {layers} (rule 6; transform not checked)"))
    return msgs


def main(argv: list[str]) -> int:
    catalog_path = argv[argv.index("--catalogo") + 1] if "--catalogo" in argv else os.environ.get("CATALOG_CSV")
    if "--json" in argv:
        tl = load_json(argv[argv.index("--json") + 1])
    elif "--vivo" in argv:
        tl = load_live()
    else:
        print(__doc__)
        return 1
    msgs = check(tl, load_catalog(catalog_path))
    print(f"timeline '{tl['nome']}' ({tl['fps']} fps) | {len(tl['trilhas'])} tracks")
    for level, text in msgs:
        print(f"{level:<5} {text}")
    errors = sum(1 for n, _ in msgs if n == "ERRO")
    warns = sum(1 for n, _ in msgs if n == "AVISO")
    print(f"summary: {errors} error(s), {warns} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
