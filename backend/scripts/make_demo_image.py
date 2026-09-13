"""Generate minimal synthetic scanned document for OCR demonstration.

Produces a clean, synthetic government ID document image for testing OCR
extraction without real PII.
"""

from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def create_demo_identity_image(output_path: Path) -> Path:
    """Create a synthetic identity document image."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Image dimensions
    width, height = 700, 420
    image = Image.new("RGB", (width, height), color="#FFFFFF")
    draw = ImageDraw.Draw(image)

    # Draw card border and background accents
    draw.rounded_rectangle([(15, 15), (width - 15, height - 15)], radius=16, outline="#2A3B5C", width=3)
    draw.rectangle([(18, 18), (width - 18, 75)], fill="#2A3B5C")

    # Header and body fonts
    font_header = None
    font_body = None
    font_footer = None

    for font_path in [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "arial.ttf",
    ]:
        if Path(font_path).exists() or font_path == "arial.ttf":
            try:
                font_header = ImageFont.truetype(font_path, 22)
                font_body = ImageFont.truetype(font_path, 20)
                font_footer = ImageFont.truetype(font_path, 14)
                break
            except Exception:
                continue

    if font_header is None:
        font_header = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_footer = ImageFont.load_default()

    draw.text((35, 30), "GOVERNMENT ID — DEMO ONLY", fill="#FFFFFF", font=font_header)

    # Document Fields (minimal, non-PII per user instruction)
    lines = [
        "Name: Demo Applicant",
        "Date of Birth: 15/03/1995",
        "Address: 123 Example Road",
    ]

    start_y = 110
    line_spacing = 70

    for i, line_text in enumerate(lines):
        y = start_y + i * line_spacing
        draw.text((45, y), line_text, fill="#1A202C", font=font_body)
        draw.line([(45, y + 42), (width - 45, y + 42)], fill="#E2E8F0", width=1)

    # Footer note
    draw.text((45, height - 38), "SYNTHETIC DEMO DATA ONLY — NOT A REAL IDENTIFICATION DOCUMENT", fill="#718096", font=font_footer)

    image.save(output_path, format="PNG")
    return output_path


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    sample_path = base_dir / "data" / "sample_documents" / "identity_scan.png"
    created = create_demo_identity_image(sample_path)
    print(f"Created demo image at: {created}")
