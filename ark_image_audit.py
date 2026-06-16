#!/usr/bin/env python3
import argparse
import base64
import json
import os
import urllib.request
from pathlib import Path


AD_AUDIT_PROMPT = """Audit every visible text string in this product advertisement image.
Return JSON only.

Tasks:
1. Transcribe every visible text region exactly as rendered.
2. Classify each region as English, valid Russian, Chinese, or corrupted/fake text.
3. Mark Russian spelling errors, truncated words, mixed alphabets, and unreadable glyphs.
4. State whether any Chinese characters remain.
5. State whether all intended Russian copy is correctly rendered.

Intended Russian copy:
- Универсальный стиль — любовь с первого взгляда
- Стиль — это не только то, что замечают, но и то, что запоминают.
- Скрытая элегантность проявляется естественно.
- Элегантность
- Модно
- Стиль | Тренд | Качество
"""


SPEC_AUDIT_PROMPT = """Audit every visible text string in this product specification image.
Return JSON only.

Tasks:
1. Transcribe every visible text region exactly as rendered.
2. Classify each region as English, number/unit, valid Russian, Chinese, or corrupted/fake text.
3. Mark any remaining Chinese characters.
4. Mark Russian spelling errors, truncated words, mixed alphabets, and unreadable glyphs.
5. Check whether product specification information is preserved rather than replaced by generic advertising copy.
6. Check whether these important values remain visible if present in the original: 30CM, 24CM, 12CM, 0.7KG, A4, ipad.
7. Check whether the table/grid and measurement-line structure are preserved.

Return fields:
- text_regions
- any_chinese_characters_present
- corrupted_or_fake_text_present
- preserved_numbers_and_units
- table_structure_preserved
- specification_meaning_preserved
- critical_issues
"""


AUDIT_PROMPTS = {
    "ad": AD_AUDIT_PROMPT,
    "spec": SPEC_AUDIT_PROMPT,
}


def data_uri(path):
    suffix = Path(path).suffix.lower()
    mime = "image/png" if suffix == ".png" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(Path(path).read_bytes()).decode()}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    parser.add_argument("--model", default="doubao-seed-2-0-pro-260215")
    parser.add_argument("--prompt-mode", choices=sorted(AUDIT_PROMPTS), default="ad")
    args = parser.parse_args()
    api_key = os.getenv("ARK_API_KEY")
    if not api_key:
        raise RuntimeError("ARK_API_KEY is missing")
    payload = json.dumps({
        "model": args.model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": AUDIT_PROMPTS[args.prompt_mode]},
                {"type": "image_url", "image_url": {"url": data_uri(args.image)}},
            ],
        }],
        "response_format": {"type": "json_object"},
        "temperature": 0,
    }).encode()
    request = urllib.request.Request(
        "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        result = json.load(response)
    content = result["choices"][0]["message"]["content"]
    output = Path(args.image).with_suffix(".audit.json")
    try:
        audit = json.loads(content)
    except json.JSONDecodeError:
        audit = {"raw_content": content}
    output.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
