"""Shared helpers: configuration from environment / .env and versioned output names."""

from __future__ import annotations

import os
import pathlib

try:  # python-dotenv is optional; plain environment variables work too
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


def env(name: str, default: str | None = None) -> str | None:
    """Read a setting from the environment (or .env)."""
    value = os.environ.get(name, default)
    return value if value not in ("", None) else default


def next_version(folder: str | os.PathLike, stem: str, ext: str) -> pathlib.Path:
    """Return <folder>/<stem>_vNN.<ext> with the first free NN. Never overwrites."""
    folder = pathlib.Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    n = 1
    while (folder / f"{stem}_v{n:02d}.{ext}").exists():
        n += 1
    return folder / f"{stem}_v{n:02d}.{ext}"


def mmss(seconds: float) -> str:
    """Format seconds as m:ss.s."""
    return f"{int(seconds // 60)}:{seconds % 60:04.1f}"
