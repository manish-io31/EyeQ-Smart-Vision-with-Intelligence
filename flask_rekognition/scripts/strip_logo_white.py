"""Strip white paper background from eyeq-logo.png copies."""
from pathlib import Path

from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PATHS = [
    ROOT / "static/img/eyeq-logo.png",
    ROOT / "flask_rekognition/static/img/eyeq-logo.png",
    ROOT / "flask_rekognition/flask_rekognition/static/img/eyeq-logo.png",
]


def remove_white(
    src: Path,
    *,
    bright_floor: float = 232.0,
    sat_max: float = 40.0,
    soft: float = 18.0,
) -> None:
    img = Image.open(src).convert("RGBA")
    arr = np.array(img, dtype=np.float32)
    r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    sat = mx - mn
    br = np.clip((mn - (bright_floor - soft)) / soft, 0.0, 1.0)
    neut = np.clip((sat_max - sat) / sat_max, 0.0, 1.0)
    remove = br * neut
    new_a = np.clip(a * (1.0 - remove), 0.0, 255.0)
    arr[:, :, 3] = new_a
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
    out.save(src, format="PNG", optimize=True)


def main() -> None:
    for p in PATHS:
        if p.exists():
            remove_white(p)
            print("OK", p.relative_to(ROOT))


if __name__ == "__main__":
    main()
