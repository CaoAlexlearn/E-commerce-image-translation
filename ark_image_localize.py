#!/usr/bin/env python3
import argparse
import base64
import json
import os
import time
import urllib.request
from datetime import datetime
from pathlib import Path


AD_PROMPT = """Edit the provided Chinese product advertisement image into a Russian-language advertisement.

Critical constraints:
- Preserve the backpack, its exact shape, color, leather texture, zippers, straps, proportions, reflections, and position.
- Preserve the original canvas composition, background, flowers, decorative circles, and the English word BACKPACK.
- Remove every Chinese character from the image.
- Replace only the Chinese advertising copy with the exact Russian text below. Do not invent text. Do not output Chinese.
- Every visible Russian word must be correctly spelled Cyrillic Russian, with no fake letters, corrupted glyphs, or mixed alphabets.
- Use an elegant serif typeface similar to the original Chinese typography.
- Keep a clear visual hierarchy and avoid overlapping the backpack.

Exact replacements:
1. Main headline: "Универсальный стиль — любовь с первого взгляда"
2. Body copy: "Стиль — это не только то, что замечают, но и то, что запоминают."
3. Secondary body copy: "Скрытая элегантность проявляется естественно."
4. Left circle label: "Элегантность"
5. Right circle label: "Модно"
6. Right-side vertical decorative copy: "Стиль | Тренд | Качество"

Render the exact Russian text legibly. Before returning the image, verify that no Chinese characters remain."""


SPEC_PROMPT = """Edit the provided Chinese product specification image into a Russian-language product specification sheet.

Critical constraints:
- This is a specification/parameter/size chart, not a lifestyle advertisement. Preserve its information structure.
- Preserve the backpack images, tablet/magazine comparison image, measurement lines, table grid, layout, numbers, units, and all product parameter values.
- Do not replace the content with generic advertising copy.
- Remove every Chinese character from the image.
- Translate only Chinese labels and Chinese descriptions into concise Russian.
- Keep English words, numbers, and units exactly unless they are part of a Chinese label.
- Preserve sizes exactly: 30CM, 24CM, 12CM, 0.7KG, A4, ipad if present.
- Preserve product attributes such as style, material, usage, fittings, color, weight, structure, size notes, and capacity/comparison descriptions.
- Every visible Russian word must be correctly spelled Cyrillic Russian, with no fake letters, corrupted glyphs, mixed alphabets, or unreadable glyphs.
- Use clean sans-serif table typography. Keep text inside table cells and avoid overlapping product images.

Suggested Russian translations for common labels:
- 产品参数 -> Характеристики товара
- 风格 -> Стиль
- 简约雅致格调 -> Лаконичный элегантный стиль
- 用途 -> Назначение
- 单肩、双肩、手提、胸挎 -> На одно плечо, рюкзак, ручная кладь, нагрудное ношение
- 颜色 -> Цвет
- 双包可选 -> Два цвета на выбор
- 规格 -> Размер
- 宽24 高30 厚12 CM -> Ширина 24, высота 30, толщина 12 CM
- 面料 -> Материал
- 牛皮材质 -> Натуральная кожа
- 配件 -> Фурнитура
- 亮泽五金 -> Блестящая металлическая фурнитура
- 重量 -> Вес
- 0.7KG -> 0.7KG
- 结构 -> Конструкция
- 证件袋、主袋、暗侧袋、隔层袋 -> Карман для документов, основное отделение, скрытый боковой карман, отделение-перегородка
- 注：请务必仔细查看产品尺寸（测量手法不同，误差1-3CM均属正常） -> Примечание: внимательно проверьте размеры товара. Из-за разных способов измерения возможна погрешность 1-3CM.
- 包包 ipad/A4杂志对比展示 -> Сравнение вместимости: ipad / журнал A4

Before returning the image, verify that no Chinese characters remain and that all numbers, units, measurement lines, and table meanings are preserved."""


PROMPTS = {
    "ad": AD_PROMPT,
    "spec": SPEC_PROMPT,
}


def data_uri(path):
    suffix = Path(path).suffix.lower()
    mime = "image/png" if suffix == ".png" else "image/jpeg"
    encoded = base64.b64encode(Path(path).read_bytes()).decode()
    return f"data:{mime};base64,{encoded}"


def request_image(api_key, model, image_path, prompt, size, timeout):
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "image": data_uri(image_path),
        "size": size,
        "response_format": "url",
        "watermark": False,
        "sequential_image_generation": "disabled",
    }).encode()
    request = urllib.request.Request(
        "https://ark.cn-beijing.volces.com/api/v3/images/generations",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description="Localize a product image using Volcengine Seedream.")
    parser.add_argument("input")
    parser.add_argument("--output", default="ark-image-output")
    parser.add_argument("--model", default="doubao-seedream-4-5-251128")
    parser.add_argument("--prompt-mode", choices=sorted(PROMPTS), default="ad")
    parser.add_argument("--size", default="2K")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()

    api_key = os.getenv("ARK_API_KEY")
    if not api_key:
        raise RuntimeError("ARK_API_KEY is missing")

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = Path(args.output) / run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    prompt = PROMPTS[args.prompt_mode]
    started = time.perf_counter()
    result = request_image(api_key, args.model, args.input, prompt, args.size, args.timeout)
    duration = time.perf_counter() - started
    (output_dir / "response.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    image_url = result["data"][0]["url"]
    extension = Path(args.input).suffix.lower() or ".png"
    output_path = output_dir / f"{Path(args.input).stem}-seedream-{args.prompt_mode}{extension}"
    urllib.request.urlretrieve(image_url, output_path)
    report = {
        "model": args.model,
        "input": str(args.input),
        "output": str(output_path),
        "prompt_mode": args.prompt_mode,
        "duration_seconds": round(duration, 2),
        "prompt": prompt,
    }
    (output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
