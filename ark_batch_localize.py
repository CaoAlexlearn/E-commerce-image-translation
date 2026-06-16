#!/usr/bin/env python3
import argparse
import csv
import json
import os
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from ark_image_localize import PROMPTS, request_image


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
SPEC_KEYWORDS = ("参数图", "参数", "规格", "尺寸", "尺码", "详情参数")


def image_paths(input_path):
    path = Path(input_path)
    if path.is_file():
        return [path]
    return sorted(
        item for item in path.rglob("*")
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS
    )


def detect_prompt_mode(path):
    normalized = path.stem.lower()
    if any(keyword.lower() in normalized for keyword in SPEC_KEYWORDS):
        return "spec"
    return "ad"


def translated_name(path, prompt_mode):
    return f"{path.stem}-seedream-{prompt_mode}{path.suffix.lower() or '.jpg'}"


def relative_output(input_root, image_path, run_output_root, prompt_mode):
    input_root = Path(input_root)
    if input_root.is_file():
        return Path(run_output_root) / translated_name(image_path, prompt_mode)
    relative = image_path.relative_to(input_root)
    return Path(run_output_root) / relative.parent / translated_name(image_path, prompt_mode)


def download_image(url, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, output_path)


def process_image(api_key, image_path, output_path, prompt_mode, args):
    started = time.perf_counter()
    result = request_image(
        api_key,
        args.model,
        image_path,
        PROMPTS[prompt_mode],
        args.size,
        args.timeout,
    )
    download_image(result["data"][0]["url"], output_path)
    return {
        "input": str(image_path),
        "output": str(output_path),
        "status": "review",
        "prompt_mode": prompt_mode,
        "model": args.model,
        "duration_seconds": round(time.perf_counter() - started, 2),
        "review_reasons": ["seedream_requires_manual_review"],
        "usage": result.get("usage", {}),
    }, result


def main():
    parser = argparse.ArgumentParser(description="Batch localize product images with Volcengine Seedream.")
    parser.add_argument("input", help="Input image or folder")
    parser.add_argument("output", nargs="?", default="ark-image-output", help="Output root folder")
    parser.add_argument("--model", default="doubao-seedream-4-5-251128")
    parser.add_argument("--size", default="2K")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--prompt-mode", choices=["auto", "ad", "spec"], default="auto")
    args = parser.parse_args()

    api_key = os.getenv("ARK_API_KEY")
    if not api_key:
        raise RuntimeError("ARK_API_KEY is missing. Load it from .env before running.")

    paths = image_paths(args.input)
    if not paths:
        raise ValueError(f"No images found in {args.input}")

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_output_root = Path(args.output) / run_id
    run_output_root.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    reports = []

    for image_path in paths:
        prompt_mode = detect_prompt_mode(image_path) if args.prompt_mode == "auto" else args.prompt_mode
        output_path = relative_output(args.input, image_path, run_output_root, prompt_mode)
        try:
            report, raw_response = process_image(api_key, image_path, output_path, prompt_mode, args)
            response_path = output_path.with_suffix(".response.json")
            response_path.write_text(
                json.dumps(raw_response, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as error:
            report = {
                "input": str(image_path),
                "output": "",
                "status": "error",
                "prompt_mode": prompt_mode,
                "model": args.model,
                "duration_seconds": 0,
                "review_reasons": [f"{type(error).__name__}: {error}"],
                "usage": {},
            }
        reports.append(report)
        print(f"{report['status']:>6} {prompt_mode:>4} {image_path} -> {report['output'] or '(no output)'}")

    summary = {
        "run_id": run_id,
        "input": str(args.input),
        "output": str(run_output_root),
        "model": args.model,
        "image_count": len(reports),
        "duration_seconds": round(time.perf_counter() - started, 2),
        "status_counts": {
            status: sum(1 for report in reports if report["status"] == status)
            for status in ("review", "error")
        },
        "images": reports,
    }
    report_path = run_output_root / "report.json"
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    with (run_output_root / "report.csv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["status", "prompt_mode", "duration_seconds", "input", "output", "review_reasons"])
        for report in reports:
            writer.writerow([
                report["status"],
                report["prompt_mode"],
                report["duration_seconds"],
                report["input"],
                report["output"],
                ";".join(report["review_reasons"]),
            ])

    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
