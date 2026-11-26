# Ambientes virtuais / Virtual environments

Dois ambientes separados evitam o conflito clássico: `pip install whisperx` troca o PyTorch CUDA pela versão CPU.
Two separate environments avoid the classic conflict: `pip install whisperx` swaps the CUDA PyTorch for the CPU build.

| Ambiente / Env | Para que serve / Used for | Arquivo / File |
|---|---|---|
| `.venv` (CPU) | passos 1, 2, 4, 5, `montagem/`, `estilo/`, testes | `requirements.txt` (+ `requirements-dev.txt`) |
| `.venv-gpu` | passo 3 (WhisperX) e `florence_quadros.py` | `requirements-gpu.txt` |

## CPU
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
pytest -q && ruff check .
```

## GPU (NVIDIA)
```bash
python -m venv .venv-gpu && source .venv-gpu/bin/activate
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126   # CUDA build first
pip install -r requirements-gpu.txt
# whisperx may replace torch with the CPU build; if so, force the CUDA wheels back:
pip install --force-reinstall --no-deps torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
python -c "import torch; print(torch.cuda.is_available())"     # must print True
```
Notas / notes
- Um trabalho de GPU por vez (8 GB de VRAM: RTX 3060). One GPU job at a time on 8 GB of VRAM.
- Florence-2 pede `flash_attn`; o script usa um patch e `attn_implementation="eager"`. Florence-2 asks for `flash_attn`; the script patches it out.
- O modelo de rosto YuNet (`.onnx`) é baixado à parte (OpenCV Zoo) e apontado em `YUNET_MODEL`. The YuNet face model is downloaded separately (OpenCV Zoo) and referenced in `YUNET_MODEL`.
