# 参考实现和第三方数据

本项目没有 fork 或逐行修改上游工程。`coinlab/baseline.py` 为自行编写的 Otsu 连通域基线；`coinlab/improved.py` 为在此基线上实现的改进。实验报告中的“代码修改”指本工程从基线流程到改进流程的变化。

算法思路参考以下 scikit-image 官方资料，数据和接口均通过正式库调用，不复制上游示例源文件。

1. Comparing edge-based and region-based segmentation
   https://scikit-image.org/docs/stable/auto_examples/applications/plot_coins_segmentation.html
2. Watershed segmentation（距离变换和标记控制分水岭）
   https://scikit-image.org/docs/stable/auto_examples/segmentation/plot_watershed.html
3. h_maxima API（峰高抑制）
   https://scikit-image.org/docs/stable/api/skimage.morphology.html#skimage.morphology.h_maxima
4. coins 数据说明
   https://scikit-image.org/docs/stable/api/skimage.data.html#skimage.data.coins

scikit-image 使用 BSD-3-Clause 许可证，详见 https://github.com/scikit-image/scikit-image/blob/main/LICENSE.txt 。NumPy、SciPy、Matplotlib、Pillow、python-docx 的许可证分别适用于它们自身；本工程的 MIT 许可证不改变第三方许可。

`data/real/coins.png` 来源于 Brooklyn Museum Collection。官方注明无已知版权限制，不将其标为本项目原创或 MIT 图像。合成图像、生成器、评估代码、可视化和实验文字为本工程产物。
