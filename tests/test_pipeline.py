"""Fast tests that need no GPU, no model download and no third-party media."""

import csv
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cacador"))
sys.path.insert(0, str(ROOT / "montagem"))

import common  # noqa: E402
import conferir_timeline as ct  # noqa: E402
import legenda_blocos as lb  # noqa: E402


def test_next_version_never_overwrites(tmp_path):
    first = common.next_version(tmp_path, "x", "csv")
    first.write_text("a")
    assert common.next_version(tmp_path, "x", "csv").name == "x_v02.csv"


def test_mmss():
    assert common.mmss(75.25) == "1:15.2"


def test_blocks_respect_max_and_pause():
    words = [{"w": w, "t0": i * 0.3, "t1": i * 0.3 + 0.2} for i, w in enumerate("um dois tres quatro cinco".split())]
    blocks = lb.make_blocks(words, 2, 0.35)
    assert [len(b) for b in blocks] == [2, 2, 1]


def test_keyword_skips_stopwords():
    assert lb.keyword_index(["o", "teste", "de"]) == 1
    assert lb.keyword_index(["o", "de"]) is None


def test_timeline_flags_baked_and_overlap():
    tl = {
        "nome": "t",
        "fps": 25,
        "trilhas": [
            {"tipo": "video", "n": 1, "clipes": [{"nome": "render_final", "ini": 0, "fim": 10}]},
            {"tipo": "audio", "n": 1, "clipes": [{"nome": "a", "ini": 0, "fim": 10}, {"nome": "b", "ini": 5, "fim": 15}]},
        ],
    }
    levels = [m[0] for m in ct.check(tl, set())]
    assert levels.count("ERRO") == 2


def test_example_timeline_exit_code():
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "montagem" / "conferir_timeline.py"),
            "--json",
            str(ROOT / "exemplos" / "timeline_exemplo.json"),
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 1 and "summary: 2 error(s)" in r.stdout


def test_prepare_reports_missing_and_never_moves(tmp_path):
    lib = ROOT / "exemplos" / "biblioteca_exemplo"
    mat = tmp_path / "m.csv"
    mat.write_text("item,id,caminho,uso,bloco,palavra,db,inicio_s,duracao_max_s\nsfx01,SFX001,,x,1,y,,,\nsfx02,NOPE,,x,1,y,,,\n")
    dest = tmp_path / "out" / "importar"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "montagem" / "preparar_video.py"),
            "--materiais",
            str(mat),
            "--destino",
            str(dest),
            "--biblioteca",
            str(lib),
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2
    assert (dest / "beep_low.wav").exists() and (lib / "sfx" / "beep_low.wav").exists()


def test_funnel_on_synthetic_clip(tmp_path):
    pytest.importorskip("cv2")
    pytest.importorskip("librosa")
    ex = ROOT / "exemplos"
    run = lambda *a: subprocess.run([sys.executable, *map(str, a)], capture_output=True, text=True, check=True)  # noqa: E731
    run(ROOT / "cacador" / "01_opencv_marcar.py", ex / "clip_sintetico.mp4", tmp_path / "opencv_v01.csv")
    run(ROOT / "cacador" / "02_audio_eventos.py", ex / "clip_16k_mono.wav", tmp_path / "audio_eventos_v01.csv")
    (tmp_path / "palavras_v01.json").write_text((ex / "saidas" / "palavras_v01.json").read_text())
    run(ROOT / "cacador" / "04_candidatos.py", ex / "clip_sintetico.mp4", tmp_path)
    rows = list(csv.DictReader(open(tmp_path / "candidatos_v01.csv", encoding="utf-8")))
    assert len(rows) >= 3
    assert any("pancada" in r["sinais"] for r in rows)
    json.dump({}, open(tmp_path / "florence_v01.json", "w"))
    run(ROOT / "cacador" / "05_tabela.py", tmp_path)
    assert (tmp_path / "tabela_cacador_v01.md").exists()
