"""Funnel step 3: per-word timing with WhisperX forced alignment.

It aligns a transcript that ALREADY exists (e.g. produced by faster-whisper large-v3); it does not
transcribe again. Words the transcriber got wrong stay wrong; only their timing is refined.
Needs the GPU environment (see docs/venvs.md). Language comes from WHISPER_LANG (default "pt").

Input JSON:  [{"start": 0.0, "end": 2.1, "text": "..."}, ...]
Usage: python cacador/03_alinhar_whisperx.py audio.wav transcript.json OUT.json
"""

from __future__ import annotations

import json
import sys

from common import env


def main(wav: str, transcript: str, out_json: str) -> None:
    import whisperx  # heavy import kept local so the other steps run without it

    device = env("DEVICE", "cuda")
    audio = whisperx.load_audio(wav)
    with open(transcript, encoding="utf-8") as fh:
        segments = [{"start": s["start"], "end": s["end"], "text": s["text"]} for s in json.load(fh)]
    model, meta = whisperx.load_align_model(language_code=env("WHISPER_LANG", "pt"), device=device)
    result = whisperx.align(segments, model, meta, audio, device, return_char_alignments=False)
    out = [
        {
            "start": s["start"],
            "end": s["end"],
            "text": s["text"],
            "palavras": [{"w": w["word"], "t0": w.get("start"), "t1": w.get("end")} for w in s.get("words", [])],
        }
        for s in result["segments"]
    ]
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    missing = sum(1 for s in out for w in s["palavras"] if w["t0"] is None)
    print("ok", len(out), "segments,", sum(len(s["palavras"]) for s in out), "words,", missing, "without timing")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
