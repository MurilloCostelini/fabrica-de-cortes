"""Close the loop feedback -> guide.

Reads feedback_*.md files, collects the lines under the section "Guia que pode precisar de ajuste"
(or "Qual guia ... deveria mudar") and, for each guide named in backticks, checks whether a newer
version of that guide exists (a hint that the feedback was applied; a human confirms).
READ-ONLY, except --novo, which creates a new feedback file from the template (never overwrites).

Usage:
  python feedback/feedback_pendente.py                 list what is still pending (short)
  python feedback/feedback_pendente.py --novo <task>   create feedback_<task>_<date>_vNN.md
Env: GUIDES_DIR (root of the guides, scanned recursively), FEEDBACK_DIR (default GUIDES_DIR/feedback)
"""

from __future__ import annotations

import datetime
import glob
import os
import re
import sys

GUIDES = os.environ.get("GUIDES_DIR", "docs")
FEEDBACK = os.environ.get("FEEDBACK_DIR", os.path.join(GUIDES, "feedback"))
SECTION = re.compile(r"^##\s*(guia que pode precisar|qual guia)", re.I)
NAMED = re.compile(r"`([^`]+?)`")
TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modelo_feedback.md")


def all_versions() -> dict[str, list[tuple[float, str]]]:
    """Index every guide by its name without the _vNN suffix, with modification times."""
    index: dict[str, list[tuple[float, str]]] = {}
    for p in glob.glob(os.path.join(GUIDES, "**", "*.md"), recursive=True):
        parts = p.replace("\\", "/").split("/")
        if "antigas" in parts or any(x.startswith("_lixo") for x in parts):
            continue
        name = os.path.basename(p)
        key = re.sub(r"_v\d+", "", name[:-3])
        index.setdefault(key, []).append((os.path.getmtime(p), name))
    return index


def new_feedback(task: str) -> str:
    today = datetime.date.today().isoformat()
    n = 1
    while os.path.exists(os.path.join(FEEDBACK, f"feedback_{task}_{today}_v{n:02d}.md")):
        n += 1
    os.makedirs(FEEDBACK, exist_ok=True)
    path = os.path.join(FEEDBACK, f"feedback_{task}_{today}_v{n:02d}.md")
    with open(TEMPLATE_PATH, encoding="utf-8") as fh:
        text = fh.read().format(t=task, d=today)
    with open(path, "x", encoding="utf-8") as fh:
        fh.write(text)
    return path


def pending() -> int:
    index = all_versions()
    total = 0
    for path in sorted(glob.glob(os.path.join(FEEDBACK, "feedback_*.md"))):
        mtime = os.path.getmtime(path)
        lines, inside = [], False
        with open(path, encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                if line.startswith("## "):
                    inside = bool(SECTION.match(line))
                    continue
                if inside and line.strip().startswith("-"):
                    lines.append(line.strip()[1:].strip())
        if not lines:
            continue
        print(f"\n{os.path.basename(path)}")
        for line in lines:
            state = "PENDENTE"
            for name in NAMED.findall(line):
                key = re.sub(r"_v\d+", "", os.path.basename(name.replace("\\", "/")).replace(".md", ""))
                newer = [f for (m, f) in index.get(key, []) if m > mtime]
                if newer:
                    state = "newer version exists: " + sorted(newer)[-1] + " (check)"
                    break
            total += state == "PENDENTE"
            print(f"  [{state}] {line[:110]}")
    print(f"\npending without a newer version: {total}")
    return total


if __name__ == "__main__":
    if "--novo" in sys.argv:
        print("created:", new_feedback(sys.argv[sys.argv.index("--novo") + 1]))
    else:
        pending()
