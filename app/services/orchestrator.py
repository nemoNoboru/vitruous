"""
Orchestrator Service

Coordinates band detection, row grouping, and densitometry analysis.
"""

from typing import TypedDict, Optional

from PIL import Image

from app.services.band_detection import detect_bands, DetectedBand
from app.services.row_grouping import group_bands_into_rows, Row
from app.services.densitometry import calculate_all_band_intensities, calculate_profile, BandWithIntensity, Profile


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
    y_tolerance: Optional[float] = None
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
) -> Optional[AnalysisResult]:
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


def clear_cache(image_path: Optional[str] = None) -> None:
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
