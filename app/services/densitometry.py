"""
Densitometry Service

Calculates intensity metrics for detected bands in western blot images.
"""

from typing import TypedDict

import numpy as np
from PIL import Image

from app.services.band_detection import DetectedBand, BBox


class IntensityMetrics(TypedDict):
    total: float
    mean: float
    max: float
    min: float
    integrated_density: float
    background_corrected: float
    relative: float


class ProfileStats(TypedDict):
    min: float
    max: float
    mean: float
    std: float


class Profile(TypedDict):
    values: list[float]
    stats: ProfileStats


class BandWithIntensity(TypedDict):
    id: int
    bbox: BBox
    intensity: IntensityMetrics


def calculate_band_intensity(image: np.ndarray, band: DetectedBand) -> IntensityMetrics:
    """
    Calculate intensity metrics for a single band.

    Args:
        image: Grayscale image as numpy array (0-255)
        band: Detected band with bounding box

    Returns:
        Dictionary of intensity metrics
    """
    bbox = band['bbox']
    x1, y1, x2, y2 = bbox['x1'], bbox['y1'], bbox['x2'], bbox['y2']

    # Clamp coordinates to image bounds
    h, w = image.shape[:2]
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(w, x2)
    y2 = min(h, y2)

    region = image[y1:y2, x1:x2]

    if region.size == 0:
        return {
            'total': 0.0,
            'mean': 0.0,
            'max': 0.0,
            'min': 0.0,
            'integrated_density': 0.0,
            'background_corrected': 0.0,
            'relative': 0.0,
        }

    # Invert for western blots (dark bands on light background = high signal)
    inverted = 255 - region.astype(np.float64)

    total = float(np.sum(inverted))
    mean = float(np.mean(inverted))
    max_val = float(np.max(inverted))
    min_val = float(np.min(inverted))
    area = region.shape[0] * region.shape[1]
    integrated_density = mean * area

    # Background estimation using edge pixels
    edge_pixels = np.concatenate([
        inverted[0, :],      # top edge
        inverted[-1, :],     # bottom edge
        inverted[:, 0],      # left edge
        inverted[:, -1],     # right edge
    ])
    background = float(np.median(edge_pixels))
    background_corrected = total - (background * area)

    return {
        'total': round(total, 2),
        'mean': round(mean, 2),
        'max': round(max_val, 2),
        'min': round(min_val, 2),
        'integrated_density': round(integrated_density, 2),
        'background_corrected': round(background_corrected, 2),
        'relative': 0.0,  # Will be normalized later
    }


def calculate_all_band_intensities(
    image_path: str,
    bands: list[DetectedBand]
) -> list[BandWithIntensity]:
    """
    Calculate normalized intensities for all bands.

    Args:
        image_path: Path to the image file
        bands: List of detected bands

    Returns:
        List of bands with intensity metrics (relative values normalized to max)
    """
    image = Image.open(image_path).convert('L')  # Convert to grayscale
    image_array = np.array(image)

    results: list[BandWithIntensity] = []
    intensities = []

    for band in bands:
        metrics = calculate_band_intensity(image_array, band)
        intensities.append(metrics['integrated_density'])
        results.append({
            'id': band['id'],
            'bbox': band['bbox'],
            'intensity': metrics,
        })

    # Normalize relative values to the maximum
    if intensities:
        max_intensity = max(intensities) if max(intensities) > 0 else 1
        for i, result in enumerate(results):
            result['intensity']['relative'] = round(intensities[i] / max_intensity, 4)

    return results


def calculate_profile(image_path: str, region: BBox) -> Profile:
    """
    Calculate column-wise densitometry profile for a region.

    Args:
        image_path: Path to the image file
        region: Bounding box defining the region

    Returns:
        Profile with column-averaged values and statistics
    """
    image = Image.open(image_path).convert('L')
    image_array = np.array(image)

    x1, y1, x2, y2 = region['x1'], region['y1'], region['x2'], region['y2']

    # Clamp coordinates
    h, w = image_array.shape[:2]
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(w, x2)
    y2 = min(h, y2)

    roi = image_array[y1:y2, x1:x2]

    if roi.size == 0:
        return {
            'values': [],
            'stats': {'min': 0, 'max': 0, 'mean': 0, 'std': 0}
        }

    # Invert for western blots
    inverted = 255 - roi.astype(np.float64)

    # Column-wise mean (averaging vertically)
    profile_values = np.mean(inverted, axis=0).tolist()

    return {
        'values': [round(v, 2) for v in profile_values],
        'stats': {
            'min': round(float(np.min(profile_values)), 2),
            'max': round(float(np.max(profile_values)), 2),
            'mean': round(float(np.mean(profile_values)), 2),
            'std': round(float(np.std(profile_values)), 2),
        }
    }
