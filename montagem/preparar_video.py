"""Collect the materials of ONE video into a single folder before opening the editor.

An editor (human or LLM) writes materiais.csv, one row per sound or media file. This script:
  1. finds every file by id in the library catalog (or by path, for brand/media files);
  2. COPIES (never moves, never deletes) everything into one folder, keeping the ORIGINAL file name;
  3. does NOT cut or normalise audio: gain / start / max duration go to materiais_ajustes.csv and are
     applied in the editor's native timeline;
  4. writes materiais_relatorio.txt (short, meant to be read by the LLM), materiais_mapa.json and,
     if a file was renamed on disk, catalogo_defasado.txt (for whoever maintains the library).

Usage:
  python montagem/preparar_video.py --materiais materiais.csv --destino out/importar \
      [--biblioteca DIR] [--catalogo CATALOGO.csv] [--dry-run] [--refazer]
Env: LIBRARY_DIR (default for --biblioteca)

materiais.csv columns (UTF-8, comma): item, id, caminho, uso, bloco, palavra, db, inicio_s, duracao_max_s
The catalog needs the columns: id, caminho_relativo (relative to --biblioteca).
Exit code: 0 ready, 1 input error, 2 missing items.
"""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "cacador"))
from common import env  # noqa: E402


def num(value: str | None) -> float | None:
    value = (value or "").strip().replace(",", ".")
    return float(value) if value else None


def find_in_catalog(rows: dict, library: pathlib.Path, id_: str):
    """Return (path, warning|None). KeyError if id unknown, FileNotFoundError if not on disk."""
    rel = rows[id_]["caminho_relativo"].replace("\\", "/")
    path = library / rel
    if path.exists():
        return path, None
    # Stale catalog: the file was renamed on disk. Look for a single file in the same folder
    # whose name ends like the catalog name.
    tail = path.name
    candidates = [f for f in path.parent.glob("*") if f.is_file() and f.name.endswith(tail)] if path.parent.is_dir() else []
    if len(candidates) == 1:
        return candidates[0], f"{id_};{rel};{candidates[0].name}"
    raise FileNotFoundError(f"not found on disk: {rel}" + (f" ({len(candidates)} candidates)" if candidates else ""))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--materiais", required=True)
    ap.add_argument("--destino", required=True)
    ap.add_argument("--biblioteca", default=env("LIBRARY_DIR"))
    ap.add_argument("--catalogo", default=None)
    ap.add_argument("--dry-run", action="store_true", help="check only, copy nothing")
    ap.add_argument("--refazer", action="store_true", help="copy again even if the file already exists")
    a = ap.parse_args()

    if not a.biblioteca:
        print("ERROR: pass --biblioteca or set LIBRARY_DIR")
        return 1
    lib = pathlib.Path(a.biblioteca)
    root = lib.parent
    dest = pathlib.Path(a.destino)
    cat_csv = pathlib.Path(a.catalogo) if a.catalogo else lib / "CATALOGO.csv"
    if not cat_csv.is_file():
        print(f"ERROR: catalog not found: {cat_csv}")
        return 1
    with open(cat_csv, encoding="utf-8-sig") as fh:
        rows = {r["id"]: r for r in csv.DictReader(fh)}
    with open(a.materiais, encoding="utf-8-sig") as fh:
        items = list(csv.DictReader(fh))
    if not items:
        print("ERROR: materiais.csv is empty")
        return 1
    if not a.dry_run:
        dest.mkdir(parents=True, exist_ok=True)

    copied, same, missing, stale, mapping, adjustments, seen = [], [], [], [], {}, [], set()
    for n, r in enumerate(items, 2):
        item = (r.get("item") or "").strip()
        id_ = (r.get("id") or "").strip()
        rel_path = (r.get("caminho") or "").strip()
        label = item or f"row{n}"
        if not item or item in seen:
            missing.append(f"{label}: empty or repeated item (row {n})")
            continue
        seen.add(item)
        try:
            if id_:
                if id_ not in rows:
                    raise KeyError(f"id {id_} is not in the catalog")
                src, warning = find_in_catalog(rows, lib, id_)
                if warning:
                    stale.append(warning)
            elif rel_path:
                p = pathlib.Path(rel_path)
                src = p if p.is_absolute() else root / rel_path.replace("\\", "/")
                if not src.is_file():
                    raise FileNotFoundError(f"not found: {rel_path}")
            else:
                raise KeyError("no id and no path")
        except (KeyError, FileNotFoundError) as e:
            missing.append(f"{item}: {e.args[0] if e.args else e}")
            continue
        db, start, dmax = num(r.get("db")), num(r.get("inicio_s")), num(r.get("duracao_max_s"))
        if db is not None or start is not None or dmax is not None:
            adjustments.append((item, src.name, db, start, dmax))
        target = dest / src.name
        mapping[item] = src.name
        if a.dry_run:
            copied.append(item)
            continue
        if target.exists() and not a.refazer and target.stat().st_size == src.stat().st_size:
            same.append(item)
            continue
        shutil.copy2(src, target)
        copied.append(item)

    side = dest.parent
    report = [
        f"materiais: {a.materiais}",
        f"destino: {dest}",
        f"copied now: {len(copied)} | already there: {len(same)} | missing: {len(missing)} | stale catalog: {len(stale)}",
    ]
    if missing:
        report.append("MISSING (fix before opening the editor):")
        report += [f"- {m}" for m in missing]
    report.append("OK: folder ready, import it whole" if not missing else "NOT ready: fix the items above")
    if not a.dry_run:
        side.mkdir(parents=True, exist_ok=True)
        if adjustments:
            with open(side / "materiais_ajustes.csv", "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["item", "arquivo_original", "db_sugerido", "inicio_s", "duracao_max_s"])
                w.writerows(adjustments)
        (side / "materiais_relatorio.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
        (side / "materiais_mapa.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=1), encoding="utf-8")
        if stale:
            (side / "catalogo_defasado.txt").write_text(
                "id;catalog_path;name_on_disk\n" + "\n".join(stale) + "\n", encoding="utf-8"
            )
    print("\n".join(report))
    return 0 if not missing else 2


if __name__ == "__main__":
    sys.exit(main())
