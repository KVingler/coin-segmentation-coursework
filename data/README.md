# 数据说明

## 合成数据

- 100 张 256×320 的 8 位灰度 PNG，20 张验证、80 张测试；每种条件分别 5 和 20 张。
- 条件：uniform、uneven、touching、uneven_touching。每张随机放置 10–18 个半径 13–22 像素的圆盘。
- 白亮圆盘模拟硬币，不包含币面真实细节；叠加纹理、光照变化、高斯模糊和标准差 4 的噪声。粘连组允许轻度重叠，使用后绘制圆盘覆盖先绘制圆盘的可见区域作为实例标注。
- `*_labels.npz` 内的 `labels` 是 uint16 实例标签，0 是背景，其余正整数各代表一枚硬币的可见部分。
- `manifest.json` 记录划分、条件、独立种子、真值数量、路径和 PNG SHA256。验证与测试种子相隔 100000；各条件独立生成场景，未把同一场景的不同退化版本放进不同集合。
- `python run_experiment.py` 按 `config.json` 确定性重建数据。无需下载、无需模型训练。
- 合成数据仅用于控制变量和精确评估，不能替代大规模真实数据集。

## 真实照片

`real/coins.png` 为 `skimage.data.coins()`，303×384、uint8。来源是 Brooklyn Museum Collection，scikit-image 文档注明 **No known copyright restrictions**，这不等同于本项目给第三方图像重新授权。

数据说明：https://scikit-image.org/docs/stable/api/skimage.data.html#skimage.data.coins

人工目视计数为 24 枚（四行，每行六枚），记录在 `real/reference.json`。该计数是项目人工参考，不是上游提供的实例掩膜。真实照片仅比较计数和叠加图，不计算像素 IoU、实例 F1 或 PQ。仅一张照片无法代表真实场景总体性能。
