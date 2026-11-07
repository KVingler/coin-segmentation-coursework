"""One-command data generation, validation selection, evaluation and plotting."""
from pathlib import Path
import csv
import importlib.metadata
import json
import platform
import time
import numpy as np
from PIL import Image
from coinlab import baseline, improved
from coinlab.dataset import CONDITIONS, build_dataset, load_record
from coinlab.metrics import evaluate

ROOT = Path(__file__).resolve().parent
METHODS = ("baseline", "background_only", "watershed_only", "improved")


def write_csv(path, rows):
    with Path(path).open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_method(image, name, cfg, selected):
    args = {"min_area": cfg["min_area"], "sigma": cfg["gaussian_sigma"]}
    if name == "baseline":
        return baseline.segment(image, **args)
    return improved.segment(image, **args, **selected,
        correct_background=name != "watershed_only",
        split_touching=name != "background_only")


def aggregate(rows):
    keys = ("abs_count_error", "exact_count", "foreground_iou", "instance_f1", "pq", "milliseconds")
    output = []
    for condition in ("all", *CONDITIONS):
        for method in METHODS:
            group = [r for r in rows if r["method"] == method and
                     (condition == "all" or r["condition"] == condition)]
            output.append({"condition": condition, "method": method, "n": len(group),
                **{key: float(np.mean([r[key] for r in group])) for key in keys},
                "mae_std": float(np.std([r["abs_count_error"] for r in group], ddof=1))})
    return output


def make_figures(records, rows, summaries, selected, cfg, real_results):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from skimage.color import label2rgb
    plt.rcParams.update({"font.family": "Microsoft YaHei", "axes.unicode_minus": False,
                         "font.size": 10, "savefig.facecolor": "white"})
    folder = ROOT / "results" / "figures"
    folder.mkdir(exist_ok=True)
    names = {"baseline": "基础方法", "background_only": "仅背景校正",
             "watershed_only": "仅分水岭", "improved": "完整改进"}
    conditions_cn = ["均匀光照", "不均匀光照", "粘连", "不均匀光照与粘连"]
    chosen = [next(r for r in records if r["split"] == "test" and r["condition"] == c) for c in CONDITIONS]
    fig, axs = plt.subplots(4, 4, figsize=(11, 9))
    for row_idx, record in enumerate(chosen):
        image, truth = load_record(ROOT / "data", record)
        base = run_method(image, "baseline", cfg, selected)[0]
        pred = run_method(image, "improved", cfg, selected)[0]
        for ax, arr, title in zip(axs[row_idx], [image, label2rgb(truth, bg_label=0),
                    label2rgb(base, image, bg_label=0), label2rgb(pred, image, bg_label=0)],
                    [conditions_cn[row_idx], f"真实标注 {truth.max()} 枚",
                     f"基础方法 {base.max()} 枚", f"完整改进 {pred.max()} 枚"]):
            ax.imshow(arr, cmap="gray"); ax.set_title(title); ax.axis("off")
    fig.tight_layout(); fig.savefig(folder / "comparison.png", dpi=180); plt.close(fig)
    image, truth = load_record(ROOT / "data", chosen[-1])
    pred, steps = run_method(image, "improved", cfg, selected)
    fig, axs = plt.subplots(2, 3, figsize=(10, 5.4))
    for ax, arr, title in zip(axs.ravel(),
        [image, steps["background"], steps["corrected"], steps["mask"], steps["distance"], label2rgb(pred, image, bg_label=0)],
        ["输入图像", "开运算估计背景", "减背景后的图像", "Otsu 与形态学处理", "距离图与种子点", "分水岭实例分割"]):
        ax.imshow(arr, cmap="gray"); ax.set_title(title); ax.axis("off")
    points = np.argwhere(steps["markers"] > 0)
    if len(points):
        axs[1, 1].scatter(points[:, 1], points[:, 0], s=4, c="#ef4444")
    fig.tight_layout(); fig.savefig(folder / "pipeline.png", dpi=180); plt.close(fig)
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.4))
    colors = ["#94a3b8", "#38bdf8", "#f59e0b", "#0f766e"]
    for i, method in enumerate(METHODS):
        group = [next(r for r in summaries if r["condition"] == c and r["method"] == method) for c in CONDITIONS]
        x = np.arange(4) + (i - 1.5) * 0.19
        for ax, metric in zip(axs, ["abs_count_error", "instance_f1"]):
            ax.bar(x, [r[metric] for r in group], width=0.19, color=colors[i], label=names[method])
    for ax, title in zip(axs, ["计数平均绝对误差 越低越好", "实例 F1 越高越好"]):
        ax.set_xticks(range(4), ["均匀", "不均匀", "粘连", "不均匀与粘连"])
        ax.set_title(title); ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=0.18); ax.set_axisbelow(True)
    axs[1].set_ylim(0, 1.1)
    axs[0].legend(fontsize=8, ncol=2)
    fig.tight_layout(); fig.savefig(folder / "metrics.png", dpi=180); plt.close(fig)
    real_image = np.array(Image.open(ROOT / "data" / "real" / "coins.png"))
    fig, axs = plt.subplots(1, 3, figsize=(10, 3.2))
    axs[0].imshow(real_image, cmap="gray"); axs[0].set_title("真实硬币照片 人工计数 24 枚")
    for ax, method in zip(axs[1:], ["baseline", "improved"]):
        labels, _ = run_method(real_image, method, cfg, selected)
        ax.imshow(label2rgb(labels, real_image, bg_label=0))
        ax.set_title(f"{names[method]} {labels.max()} 枚")
    for ax in axs: ax.axis("off")
    fig.tight_layout(); fig.savefig(folder / "real.png", dpi=180); plt.close(fig)
    # Always show the worst full-method test case, with deterministic tie breaking.
    candidates = [r for r in rows if r["method"] == "improved"]
    worst = sorted(candidates, key=lambda r: (-r["abs_count_error"], r["instance_f1"], r["id"]))[0]
    record = next(r for r in records if r["split"] == "test" and r["id"] == worst["id"])
    image, truth = load_record(ROOT / "data", record)
    pred, _ = run_method(image, "improved", cfg, selected)
    fig, axs = plt.subplots(1, 3, figsize=(10, 3))
    for ax, arr, title in zip(axs, [image, label2rgb(truth, bg_label=0), label2rgb(pred, image, bg_label=0)],
        [f"最差计数样例 {record['id']}", f"真实 {truth.max()} 枚", f"预测 {pred.max()} 枚 F1={worst['instance_f1']:.3f}"]):
        ax.imshow(arr, cmap="gray"); ax.set_title(title, fontsize=9); ax.axis("off")
    fig.tight_layout(); fig.savefig(folder / "failure.png", dpi=180); plt.close(fig)
    return worst


def main():
    started = time.perf_counter()
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    (ROOT / "results").mkdir(exist_ok=True)
    records = build_dataset(ROOT / "data", cfg)
    validation = [(r, *load_record(ROOT / "data", r)) for r in records if r["split"] == "validation"]
    search = []
    for size in cfg["background_sizes"]:
        for h in cfg["h_values"]:
            selected = {"background_size": size, "h": h}
            values = [evaluate(truth, run_method(image, "improved", cfg, selected)[0]) for _, image, truth in validation]
            search.append({**selected, "mae": float(np.mean([v["abs_count_error"] for v in values])),
                           "instance_f1": float(np.mean([v["instance_f1"] for v in values]))})
    # Predeclared selection rule: min MAE, max F1, then smaller size and h.
    best = min(search, key=lambda v: (v["mae"], -v["instance_f1"], v["background_size"], v["h"]))
    selected = {key: best[key] for key in ("background_size", "h")}
    (ROOT / "results" / "selected_params.json").write_text(json.dumps(selected, indent=2), encoding="utf-8")
    write_csv(ROOT / "results" / "validation_search.csv", search)
    rows = []
    # Warm up imports/implementations before per-image timings.
    for method in METHODS: run_method(validation[0][1], method, cfg, selected)
    for record in records:
        if record["split"] != "test": continue
        image, truth = load_record(ROOT / "data", record)
        for method in METHODS:
            tick = time.perf_counter()
            labels, _ = run_method(image, method, cfg, selected)
            elapsed = 1000 * (time.perf_counter() - tick)
            rows.append({"id": record["id"], "condition": record["condition"], "method": method,
                         **evaluate(truth, labels), "milliseconds": elapsed})
    summaries = aggregate(rows)
    write_csv(ROOT / "results" / "per_image.csv", rows)
    write_csv(ROOT / "results" / "summary.csv", summaries)
    real_image = np.array(Image.open(ROOT / "data" / "real" / "coins.png"))
    real_results = {method: int(run_method(real_image, method, cfg, selected)[0].max()) for method in METHODS}
    worst = make_figures(records, rows, summaries, selected, cfg, real_results)
    result = {"selected_params": selected, "validation_best": best, "summary": summaries,
              "real_counts": real_results, "real_manual_count": 24, "worst_test_case": worst,
              "python": platform.python_version(), "platform": platform.platform(),
              "processor": platform.processor(),
              "packages": {p: importlib.metadata.version(p) for p in
                           ["numpy", "scipy", "scikit-image", "matplotlib", "Pillow", "python-docx"]},
              "total_seconds": time.perf_counter() - started}
    (ROOT / "results" / "experiment.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"selected": selected, "overall": summaries[:4], "real": real_results,
                      "worst": worst, "seconds": result["total_seconds"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
