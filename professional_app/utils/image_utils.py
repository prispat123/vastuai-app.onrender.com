from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageFilter, ImageStat


@dataclass(frozen=True)
class ImageQuality:
    width: int
    height: int
    sharpness: float
    brightness: float
    quality_score: int
    issues: list[str]


def uploaded_file_to_image(file_bytes: bytes, filename: str) -> Image.Image:
    """Convert a PNG/JPEG or the first page of a PDF to an RGB PIL image."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        try:
            import pypdfium2 as pdfium
        except ImportError as exc:
            raise RuntimeError(
                "PDF support requires pypdfium2. Run: pip install -r requirements.txt"
            ) from exc

        pdf = pdfium.PdfDocument(file_bytes)
        if len(pdf) == 0:
            raise ValueError("The PDF does not contain any pages.")
        page = pdf[0]
        bitmap = page.render(scale=2.0)
        image = bitmap.to_pil()
    else:
        image = Image.open(BytesIO(file_bytes))

    image = image.convert("RGB")
    image.thumbnail((1800, 1800))
    return image


def image_to_png_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def assess_image_quality(image: Image.Image) -> ImageQuality:
    gray = image.convert("L")
    width, height = image.size
    brightness = float(ImageStat.Stat(gray).mean[0])

    edges = gray.filter(ImageFilter.FIND_EDGES)
    edge_stat = ImageStat.Stat(edges)
    sharpness = float(edge_stat.var[0])

    issues: list[str] = []
    score = 100

    if min(width, height) < 600:
        issues.append("The layout resolution is low.")
        score -= 30
    if sharpness < 350:
        issues.append("The layout may be blurred or have weak line detail.")
        score -= 25
    if brightness < 45:
        issues.append("The layout is too dark.")
        score -= 25
    elif brightness > 245:
        issues.append("The layout may be overexposed or washed out.")
        score -= 15

    return ImageQuality(
        width=width,
        height=height,
        sharpness=round(sharpness, 1),
        brightness=round(brightness, 1),
        quality_score=max(0, min(100, score)),
        issues=issues,
    )
