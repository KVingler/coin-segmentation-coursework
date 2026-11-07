"""Deterministic synthetic circles; ground truth never enters segmentation.

Validation and test are independent random scenes, not transforms of the same
scene. Mild occlusions use the visible instance mask (last-drawn disk on top).
"""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import data

CONDITIONS = ("uniform", "uneven", "touching", "uneven_touching")


def make_scene(seed, condition, height=256, width=320):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[:height, :width]
    touching = "touching" in condition
    uneven = "uneven" in condition
    count = int(rng.integers(10, 19))
    circles = []
    for idx in range(count):
        for attempt in range(3000):
            radius = float(rng.uniform(13, 22))
            if touching and idx % 3 == 1:
                py, px, old_r = circles[-1]
                theta = rng.uniform(0, 2 * np.pi)
                separation = rng.uniform(0.82, 0.95) * (radius + old_r)
                cy, cx = py + np.sin(theta) * separation, px + np.cos(theta) * separation
            else:
                cy = rng.uniform(radius + 5, height - radius - 5)
                cx = rng.uniform(radius + 5, width - radius - 5)
            if not (radius + 4 < cy < height - radius - 4 and radius + 4 < cx < width - radius - 4):
                continue
            minimum = 0.80 if touching else 1.12
            if all(np.hypot(cy - y, cx - x) > minimum * (radius + r) for y, x, r in circles):
                circles.append((cy, cx, radius))
                break
        else:
            raise RuntimeError("Scene placement failed; change generator configuration")
    image = np.full((height, width), 55.0)
    truth = np.zeros((height, width), dtype=np.uint16)
    for idx, (cy, cx, radius) in enumerate(circles, start=1):
        rho = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2) / radius
        mask = rho <= 1
        tone = rng.uniform(135, 180)
        texture = 5 * np.sin(xx / 2.5 + idx) * np.cos(yy / 3.0) + 7 * (1 - rho)
        image[mask] = (tone + texture)[mask]
        truth[mask] = idx
    if uneven:
        angle = rng.uniform(0, 2 * np.pi)
        ramp = np.cos(angle) * (xx / (width - 1) - 0.5) + np.sin(angle) * (yy / (height - 1) - 0.5)
        illumination = rng.uniform(110, 165) * ramp
        illumination += 18 * np.sin(2 * np.pi * xx / width + rng.uniform(0, 6.28))
        image += illumination
    image = ndi.gaussian_filter(image, 0.65) + rng.normal(0, 4.0, image.shape)
    image = np.clip(np.rint(image), 0, 255).astype(np.uint8)
    return image, truth


def build_dataset(root, config):
    root = Path(root)
    records = []
    for split, amount, offset in [("validation", config["validation_per_condition"], 0),
                                   ("test", config["test_per_condition"], 100000)]:
        folder = root / "synthetic" / split
        folder.mkdir(parents=True, exist_ok=True)
        for c, condition in enumerate(CONDITIONS):
            for i in range(amount):
                seed = config["seed"] + offset + c * 1000 + i
                name = f"{condition}_{i:02d}"
                image, labels = make_scene(seed, condition, config["height"], config["width"])
                image_path = folder / f"{name}.png"
                label_path = folder / f"{name}_labels.npz"
                Image.fromarray(image).save(image_path)
                np.savez_compressed(label_path, labels=labels)
                records.append({"id": name, "split": split, "condition": condition,
                    "seed": seed, "count": int(labels.max()),
                    "image": image_path.relative_to(root).as_posix(),
                    "labels": label_path.relative_to(root).as_posix(),
                    "image_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest()})
    (root / "real").mkdir(parents=True, exist_ok=True)
    Image.fromarray(data.coins()).save(root / "real" / "coins.png")
    (root / "manifest.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    return records


def load_record(root, record):
    return (np.array(Image.open(Path(root) / record["image"]).convert("L")),
            np.load(Path(root) / record["labels"])["labels"])
