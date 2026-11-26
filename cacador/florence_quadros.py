"""Describe frames and read on-screen text with Florence-2 (local, GPU).

Florence-2 describes the scene (in English) and runs OCR. It does not recognise pop-culture
references; that is why step 5 has a separate, optional "reference" column filled by an LLM.

Usage: python cacador/florence_quadros.py OUT.json frame1.jpg frame2.jpg ...
Env:   FLORENCE_MODEL (default microsoft/Florence-2-large), DEVICE (default cuda)
"""

from __future__ import annotations

import json
import sys
import unittest.mock as um

from common import env


def main(out_json: str, frames: list[str]) -> None:
    import torch  # heavy imports kept local
    from PIL import Image
    from transformers import AutoModelForCausalLM, AutoProcessor
    from transformers.dynamic_module_utils import get_imports

    def without_flash_attn(filename):
        return [i for i in get_imports(filename) if i != "flash_attn"]

    device = env("DEVICE", "cuda")
    name = env("FLORENCE_MODEL", "microsoft/Florence-2-large")
    with um.patch("transformers.dynamic_module_utils.get_imports", without_flash_attn):
        model = (
            AutoModelForCausalLM.from_pretrained(
                name, trust_remote_code=True, torch_dtype=torch.float16, attn_implementation="eager"
            )
            .to(device)
            .eval()
        )
        proc = AutoProcessor.from_pretrained(name, trust_remote_code=True)

    def run(img, task):
        inputs = proc(text=task, images=img, return_tensors="pt").to(device, torch.float16)
        with torch.no_grad():
            ids = model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=256,
                num_beams=3,
                do_sample=False,
                use_cache=False,
            )
        text = proc.batch_decode(ids, skip_special_tokens=False)[0]
        return proc.post_process_generation(text, task=task, image_size=img.size)[task]

    out = {}
    for path in frames:
        img = Image.open(path).convert("RGB")
        out[path] = {"descricao": run(img, "<MORE_DETAILED_CAPTION>"), "texto": run(img, "<OCR>")}
        print(path, out[path]["descricao"][:100])
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2:])
