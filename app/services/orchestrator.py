"""
Orchestrator Service

Coordinates band detection, row grouping, and densitometry analysis.
"""

from typing import TypedDict

from PIL import Image

from app.services.band_detection import DetectedBand, detect_bands
from app.services.densitometry import BandWithIntensity, Profile, calculate_all_band_intensities, calculate_profile
from app.services.row_grouping import Row, group_bands_into_rows


class DetectionResult(TypedDict):
    width: int
    height: int
    original: str
    rows: list[Row]
    total_bands: int
    total_rows: int


class AnalysisResult(TypedDict):
    row_id: int
    bands: list[BandWithIntensity]
    profile: Profile


# Store detection results for subsequent analyze_row calls
_detection_cache: dict[str, list[Row]] = {}


def detect_blot(
    image_path: str,
    confidence_threshold: float = 0.5,
    y_tolerance: float | None = None
) -> DetectionResult:
    """
    Detect all bands in an image and group them into rows.

    Args:
        image_path: Path to the western blot image
        confidence_threshold: Minimum confidence for band detection
        y_tolerance: Y-coordinate tolerance for row grouping (auto if None)

    Returns:
        Detection result with rows and band information
    """
    # Get image dimensions
    image = Image.open(image_path)
    width, height = image.size

    # Detect bands
    bands = detect_bands(image_path, confidence_threshold)

    # Group into rows
    rows = group_bands_into_rows(bands, y_tolerance)

    # Cache for analyze_row
    _detection_cache[image_path] = rows

    return {
        'width': width,
        'height': height,
        'original': '',  # Will be set by route
        'rows': rows,
        'total_bands': sum(row['band_count'] for row in rows),
        'total_rows': len(rows),
    }


def analyze_row(
    image_path: str,
    row_id: int,
    confidence_threshold: float = 0.5
) -> AnalysisResult | None:
    """
    Analyze a specific row's band intensities.

    Args:
        image_path: Path to the western blot image
        row_id: Which row to analyze (from detect_blot results)
        confidence_threshold: Minimum confidence if re-detection needed

    Returns:
        Analysis result with intensity metrics and profile, or None if row not found
    """
    # Check cache first, re-detect if needed
    if image_path not in _detection_cache:
        detect_blot(image_path, confidence_threshold)

    rows = _detection_cache.get(image_path, [])

    # Find the requested row
    target_row = None
    for row in rows:
        if row['row_id'] == row_id:
            target_row = row
            break

    if target_row is None:
        return None

    # Calculate intensities for bands in this row
    bands_with_intensity = calculate_all_band_intensities(image_path, target_row['bands'])

    # Calculate profile for the entire row region
    profile = calculate_profile(image_path, target_row['bbox'])

    return {
        'row_id': row_id,
        'bands': bands_with_intensity,
        'profile': profile,
    }


def analyze_row_with_custom_bboxes(
    image_path: str,
    row_id: int,
    custom_bboxes: list[dict],
    confidence_threshold: float = 0.5
) -> AnalysisResult | None:
    """
    Analyze a row using user-adjusted band boundaries.

    Args:
        image_path: Path to the western blot image
        row_id: Which row to analyze
        custom_bboxes: List of custom bounding boxes [{x1, y1, x2, y2}, ...]
        confidence_threshold: Minimum confidence if re-detection needed

    Returns:
        Analysis result with recalculated intensity metrics
    """
    # Check cache first, re-detect if needed
    if image_path not in _detection_cache:
        detect_blot(image_path, confidence_threshold)

    rows = _detection_cache.get(image_path, [])

    # Find the requested row
    target_row = None
    for row in rows:
        if row['row_id'] == row_id:
            target_row = row
            break

    if target_row is None:
        return None

    # Create modified bands with custom bboxes
    modified_bands: list[DetectedBand] = []
    original_bands = target_row['bands']

    for i, bbox in enumerate(custom_bboxes):
        confidence = original_bands[i]['confidence'] if i < len(original_bands) else 1.0
        modified_band: DetectedBand = {
            'id': i,
            'bbox': {
                'x1': int(bbox['x1']),
                'y1': int(bbox['y1']),
                'x2': int(bbox['x2']),
                'y2': int(bbox['y2']),
            },
            'confidence': confidence,
            'center': {
                'x': (bbox['x1'] + bbox['x2']) / 2,
                'y': (bbox['y1'] + bbox['y2']) / 2,
            },
            'width': bbox['x2'] - bbox['x1'],
            'height': bbox['y2'] - bbox['y1'],
        }
        modified_bands.append(modified_band)

    # Calculate intensities with custom bboxes
    bands_with_intensity = calculate_all_band_intensities(image_path, modified_bands)

    # Profile stays the same (full row region)
    profile = calculate_profile(image_path, target_row['bbox'])

    return {
        'row_id': row_id,
        'bands': bands_with_intensity,
        'profile': profile,
    }


def clear_cache(image_path: str | None = None) -> None:
    """
    Clear the detection cache.

    Args:
        image_path: Clear specific image, or all if None
    """
    global _detection_cache
    if image_path is None:
        _detection_cache = {}
    elif image_path in _detection_cache:
        del _detection_cache[image_path]
