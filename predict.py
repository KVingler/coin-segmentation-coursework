"""Run the fixed, validation-selected pipeline on a new image."""
from pathlib import Path
import argparse
import json
import numpy as np
from PIL import Image
from skimage.color import label2rgb
from coinlab.improved import segment


def main():
    parser = argparse.ArgumentParser(description="硬币分割计数 输入亮目标暗背景图像")
    parser.add_argument("image", type=Path)
    parser.add_argument("--output", type=Path, default=Path("results/prediction"))
    parser.add_argument("--background-size", type=int, help="可选覆盖背景结构元素宽度")
    parser.add_argument("--h", type=float, help="可选覆盖距离峰值高度")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    cfg = json.loads((root / "config.json").read_text(encoding="utf-8"))
    selected = json.loads((root / "results/selected_params.json").read_text(encoding="utf-8"))
    if args.background_size is not None: selected["background_size"] = args.background_size
    if args.h is not None: selected["h"] = args.h
    image = np.array(Image.open(args.image).convert("L"))
    labels, _ = segment(image, min_area=cfg["min_area"], sigma=cfg["gaussian_sigma"], **selected)
    args.output.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output / "labels.npz", labels=labels)
    overlay = np.rint(label2rgb(labels, image, bg_label=0) * 255).astype(np.uint8)
    Image.fromarray(overlay).save(args.output / "overlay.png")
    info = {"input": str(args.image), "count": int(labels.max()), "parameters": selected}
    (args.output / "count.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(info, ensure_ascii=False))


if __name__ == "__main__": main()
