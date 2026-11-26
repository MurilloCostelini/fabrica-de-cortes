"""Download reference videos YOU chose (board, pin, video URL) with yt-dlp, into a NEW isolated
folder, then report exact duplicates by content hash. Nothing is overwritten or deleted.

Only run it with links you picked yourself, and respect each site's terms and the content's
licence: references are for private study (measuring style), not for reuse in published work.

Usage:
  python estilo/baixar_refs.py URL TOPIC            download into REF_DIR/ref_<topic>_<date>_vNN/brutos/
  python estilo/baixar_refs.py URL TOPIC --listar   only list the items (no download)
  python estilo/baixar_refs.py --dedup FOLDER       only report duplicates
Env: REF_DIR (default ./refs), FFPROBE (optional, for durations)
"""

from __future__ import annotations

import datetime
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys

BASE = os.environ.get("REF_DIR", "refs")
MEDIA = (".mp4", ".webm", ".mkv", ".mov", ".gif", ".jpg", ".jpeg", ".png", ".webp")


def sha(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    return h.hexdigest()


def duration(path: str) -> str:
    exe = os.environ.get("FFPROBE") or shutil.which("ffprobe")
    if not exe or not path.lower().endswith((".mp4", ".webm", ".mkv", ".mov", ".gif")):
        return ""
    try:
        r = subprocess.run(
            [exe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return f"{float(r.stdout.strip()):.1f} s"
    except (ValueError, subprocess.SubprocessError):
        return ""


def report(folder: str, extra: str = "") -> None:
    files = sorted(f for f in glob.glob(os.path.join(folder, "*")) if f.lower().endswith(MEDIA))
    seen: dict[str, str] = {}
    dup: dict[str, str] = {}
    for f in files:
        h = sha(f)
        if h in seen:
            dup[os.path.basename(f)] = seen[h]
        else:
            seen[h] = os.path.basename(f)
    # the report never goes inside the raw folder: it goes next to it
    dest = os.path.dirname(os.path.abspath(folder)) if os.path.basename(os.path.abspath(folder)).lower() == "brutos" else folder
    n = 1
    while os.path.exists(os.path.join(dest, f"relatorio_refs_v{n:02d}.md")):
        n += 1
    path = os.path.join(dest, f"relatorio_refs_v{n:02d}.md")
    lines = [
        f"# Reference report | {datetime.date.today():%Y-%m-%d}",
        f"Folder: `{folder}`",
        extra,
        f"Media items: {len(files)} | unique: {len(seen)} | exact duplicates: {len(dup)}",
        "",
        "| file | duration | duplicate of |",
        "|---|---|---|",
    ]
    for f in files:
        name = os.path.basename(f)
        lines.append(f"| {name} | {duration(f)} | {dup.get(name, '')} |")
    with open(path, "x", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"items {len(files)}, unique {len(seen)}, duplicates {len(dup)} -> {path}")


def main(argv: list[str]) -> None:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return
    if argv[0] == "--dedup":
        report(argv[1])
        return
    url, topic = argv[0], argv[1]
    ytdlp = shutil.which("yt-dlp")
    if not ytdlp:
        sys.exit("yt-dlp is not on PATH")
    if "--listar" in argv:
        r = subprocess.run(
            [ytdlp, "--flat-playlist", "-J", url], capture_output=True, text=True, encoding="utf-8", errors="ignore"
        )
        try:
            data = json.loads(r.stdout)
            items = data.get("entries") or [data]
            print(f"{len(items)} items at the link")
            for e in items[:20]:
                print("  -", (e or {}).get("title") or (e or {}).get("id"))
        except json.JSONDecodeError:
            print("could not list:", (r.stderr or "")[:300])
        return
    today = datetime.date.today().isoformat()
    n = 1
    while os.path.exists(os.path.join(BASE, f"ref_{topic}_{today}_v{n:02d}")):
        n += 1
    raw = os.path.join(BASE, f"ref_{topic}_{today}_v{n:02d}", "brutos")
    os.makedirs(raw)
    cmd = [ytdlp, "-i", "--write-info-json", "-f", "bv*+ba/b", "-o", os.path.join(raw, "%(autonumber)03d_%(id)s.%(ext)s"), url]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    errors = [line for line in (r.stderr or "").splitlines() if line.startswith("ERROR")]
    extra = f"Link: {url}\nyt-dlp errors (items that failed): {len(errors)}"
    if errors:
        extra += "\n" + "\n".join("- " + e[:160] for e in errors[:10])
    report(raw, extra)


if __name__ == "__main__":
    main(sys.argv[1:])
