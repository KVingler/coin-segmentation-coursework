"""Background correction and marker-controlled distance watershed.

Compared with baseline.py, add white top-hat background correction and replace
connected component counting with h-maxima markers plus distance watershed.
"""
import numpy as np
from scipy import ndimage as ndi
from skimage.filters import threshold_otsu
from skimage.morphology import h_maxima
from skimage.segmentation import watershed, relabel_sequential
from .baseline import clean_mask


def segment(image, min_area=120, sigma=1.0, background_size=61, h=2.0,
            correct_background=True, split_touching=True):
    image = np.asarray(image, dtype=np.float64)
    if image.ndim != 2:
        raise ValueError("Expected a 2-D grayscale image")
    if background_size < 3 or background_size % 2 == 0 or h <= 0:
        raise ValueError("background_size must be odd and >=3; h must be >0")
    smooth = ndi.gaussian_filter(image, sigma=sigma)
    # Square opening is separable and fast; its width should exceed coin diameter.
    background = (ndi.grey_opening(smooth, size=(background_size, background_size))
                  if correct_background else np.zeros_like(smooth))
    corrected = smooth - background if correct_background else smooth
    threshold = float(threshold_otsu(corrected))
    mask = clean_mask(corrected > threshold, min_area)
    distance = ndi.distance_transform_edt(mask)
    markers = np.zeros(mask.shape, dtype=np.int32)
    if split_touching and mask.any():
        peaks = h_maxima(distance, h) & mask
        markers, _ = ndi.label(peaks)
        # A small component can have no h-maximum; retain one seed in that case.
        components, n = ndi.label(mask)
        for idx in range(1, n + 1):
            region = components == idx
            if not np.any(markers[region]):
                location = np.argmax(np.where(region, distance, -1))
                markers.flat[location] = markers.max() + 1
        labels = watershed(-distance, markers, mask=mask)
        areas = np.bincount(labels.ravel())
        keep = areas >= min_area
        keep[0] = False
        labels = np.where(keep[labels], labels, 0)
        labels = relabel_sequential(labels)[0]
    else:
        labels, _ = ndi.label(mask)
    return labels.astype(np.int32), {
        "smooth": smooth, "background": background, "corrected": corrected,
        "threshold": threshold, "mask": mask, "distance": distance,
        "markers": markers,
    }
