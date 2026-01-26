"""
Row Grouping Service

Groups detected bands into rows based on Y-coordinate proximity.
"""

from typing import TypedDict

from app.services.band_detection import BBox, DetectedBand


class Row(TypedDict):
    row_id: int
    y_center: float
    bbox: BBox
    band_count: int
    bands: list[DetectedBand]


def group_bands_into_rows(bands: list[DetectedBand], y_tolerance: float | None = None) -> list[Row]:
    """
    Group bands into rows based on Y-coordinate proximity.

    Bands at similar Y-coordinates (heights) are considered to be in the same row.

    Args:
        bands: List of detected bands from band_detection
        y_tolerance: Maximum Y-distance for bands to be in same row.
                    If None, auto-calculated as 50% of median band height.

    Returns:
        List of rows sorted top-to-bottom, with bands in each row sorted left-to-right.
    """
    if not bands:
        return []

    # Auto-calculate tolerance if not provided
    if y_tolerance is None:
        heights = [band['height'] for band in bands]
        median_height = sorted(heights)[len(heights) // 2]
        y_tolerance = median_height * 0.5

    # Sort bands by Y-center
    sorted_bands = sorted(bands, key=lambda b: b['center']['y'])

    rows: list[list[DetectedBand]] = []
    current_row: list[DetectedBand] = []
    current_y_center = None

    for band in sorted_bands:
        band_y = band['center']['y']

        if current_y_center is None:
            current_row = [band]
            current_y_center = band_y
        elif abs(band_y - current_y_center) <= y_tolerance:
            current_row.append(band)
            # Update running average of Y-center
            current_y_center = sum(b['center']['y'] for b in current_row) / len(current_row)
        else:
            rows.append(current_row)
            current_row = [band]
            current_y_center = band_y

    # Don't forget the last row
    if current_row:
        rows.append(current_row)

    # Sort bands within each row left-to-right
    for row in rows:
        row.sort(key=lambda b: b['center']['x'])

    # Build Row objects
    result: list[Row] = []
    for row_id, row_bands in enumerate(rows):
        # Calculate row bounding box
        x1 = min(b['bbox']['x1'] for b in row_bands)
        y1 = min(b['bbox']['y1'] for b in row_bands)
        x2 = max(b['bbox']['x2'] for b in row_bands)
        y2 = max(b['bbox']['y2'] for b in row_bands)

        y_center = sum(b['center']['y'] for b in row_bands) / len(row_bands)

        # Re-assign band IDs within row context
        for i, band in enumerate(row_bands):
            band['id'] = i

        result.append({
            'row_id': row_id,
            'y_center': round(y_center, 1),
            'bbox': {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2},
            'band_count': len(row_bands),
            'bands': row_bands,
        })

    return result
