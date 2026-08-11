from __future__ import annotations

import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageEnhance, ImageFilter


from platform_core.config import CONFIG

CACHE_DIR = CONFIG.cache_dir / "ProfessionalFloorplans"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class PipelineTimings:
    preprocessing_seconds: float = 0.0
    ocr_seconds: float = 0.0
    vision_seconds: float = 0.0
    total_seconds: float = 0.0
    cache_hit: bool = False


def _sha256(data: bytes, mode: str, north_orientation: str) -> str:
    return hashlib.sha256(data + mode.encode() + north_orientation.encode()).hexdigest()


def preprocess_floor_plan(image_bytes: bytes, mode: str = "Fast") -> bytes:
    """Resize and lightly enhance an image for fast OCR/vision without changing geometry."""
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    max_side = 1600 if mode == "Fast" else 2400
    if max(image.size) > max_side:
        image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    image = ImageEnhance.Contrast(image).enhance(1.15)
    image = ImageEnhance.Sharpness(image).enhance(1.10)
    if mode == "Detailed":
        image = image.filter(ImageFilter.UnsharpMask(radius=1.2, percent=120, threshold=3))
    output = BytesIO()
    image.save(output, format="JPEG", quality=82 if mode == "Fast" else 90, optimize=True)
    return output.getvalue()


def extract_text_local(image_bytes: bytes) -> dict[str, Any]:
    """Optional local OCR. It degrades gracefully when Tesseract is unavailable."""
    started = time.perf_counter()
    try:
        import pytesseract  # optional dependency
        image = Image.open(BytesIO(image_bytes))
        text = pytesseract.image_to_string(image, config="--psm 11")
        labels = [line.strip() for line in text.splitlines() if line.strip()]
        return {
            "available": True,
            "text": text.strip(),
            "labels": labels[:100],
            "error": "",
            "seconds": time.perf_counter() - started,
        }
    except Exception as exc:
        return {
            "available": False,
            "text": "",
            "labels": [],
            "error": str(exc),
            "seconds": time.perf_counter() - started,
        }


def analyse_floor_plan(
    image_bytes: bytes,
    mode: str = "Fast",
    north_orientation: str = "Auto-detect",
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Run preprocessing, OCR and vision with cache and parallel execution."""
    total_started = time.perf_counter()
    cache_key = _sha256(image_bytes, mode, north_orientation)
    cache_file = CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists() and not force_refresh:
        result = json.loads(cache_file.read_text(encoding="utf-8"))
        result.setdefault("timings", {})["cache_hit"] = True
        result["timings"]["total_seconds"] = round(time.perf_counter() - total_started, 3)
        return result

    prep_started = time.perf_counter()
    processed = preprocess_floor_plan(image_bytes, mode)
    preprocessing_seconds = time.perf_counter() - prep_started

    from professional_app.agents.vision_agent import inspect_floor_plan

    detail = "low" if mode == "Fast" else "high"
    with ThreadPoolExecutor(max_workers=2) as executor:
        ocr_future = executor.submit(extract_text_local, processed)
        # The vision request starts immediately; OCR remains optional and is merged afterwards.
        vision_started = time.perf_counter()
        vision_future = executor.submit(
            inspect_floor_plan,
            processed,
            detail,
            north_orientation,
        )
        ocr = ocr_future.result()
        vision = vision_future.result()
        vision_seconds = time.perf_counter() - vision_started

    vision["ocr"] = ocr
    vision["analysis_mode"] = mode
    vision["north_orientation"] = north_orientation
    vision["cache_key"] = cache_key
    vision["timings"] = asdict(PipelineTimings(
        preprocessing_seconds=round(preprocessing_seconds, 3),
        ocr_seconds=round(float(ocr.get("seconds", 0.0)), 3),
        vision_seconds=round(vision_seconds, 3),
        total_seconds=round(time.perf_counter() - total_started, 3),
        cache_hit=False,
    ))
    cache_file.write_text(json.dumps(vision, indent=2), encoding="utf-8")
    return vision
