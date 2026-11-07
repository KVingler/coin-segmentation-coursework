"""Baseline: Gaussian denoising, global Otsu, morphology, connected components.

This is the project's own baseline, not an unmodified upstream code file.
The conceptual starting point is the scikit-image coins segmentation tutorial.
"""
import numpy as np
from scipy import ndimage as ndi
from skimage.filters import threshold_otsu


def clean_mask(mask, min_area=120):
    """Identical cleanup for all variants to keep the comparison controlled."""
    mask = ndi.binary_opening(mask, structure=ndi.generate_binary_structure(2, 1))
    mask = ndi.binary_fill_holes(mask)
    labels, _ = ndi.label(mask)
    areas = np.bincount(labels.ravel())
    keep = areas >= min_area
    keep[0] = False
    return keep[labels]


def segment(image, min_area=120, sigma=1.0):
    image = np.asarray(image, dtype=np.float64)
    if image.ndim != 2:
        raise ValueError("Expected a 2-D grayscale image")
    smooth = ndi.gaussian_filter(image, sigma=sigma)
    threshold = float(threshold_otsu(smooth))
    mask = clean_mask(smooth > threshold, min_area)
    labels, _ = ndi.label(mask)
    return labels.astype(np.int32), {"smooth": smooth, "mask": mask,
                                    "threshold": threshold}
