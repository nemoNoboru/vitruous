"""
Tests for row grouping logic.
Pure unit tests - no model needed.
"""

import pytest

from app.services.row_grouping import group_bands_into_rows


class TestGroupBandsIntoRows:
    """Test band grouping by Y-coordinate proximity."""

    def test_groups_bands_into_two_rows(self, sample_bands):
        """Test that 6 bands are grouped into 2 rows."""
        rows = group_bands_into_rows(sample_bands)

        assert len(rows) == 2
        assert rows[0]['band_count'] == 3
        assert rows[1]['band_count'] == 3

    def test_rows_sorted_top_to_bottom(self, sample_bands):
        """Test that rows are sorted by Y-coordinate (top first)."""
        rows = group_bands_into_rows(sample_bands)

        # Row 0 should be at y=50, Row 1 at y=150
        assert rows[0]['y_center'] < rows[1]['y_center']
        assert rows[0]['y_center'] == pytest.approx(50.0, abs=1)
        assert rows[1]['y_center'] == pytest.approx(150.0, abs=1)

    def test_bands_sorted_left_to_right_within_row(self, sample_bands):
        """Test that bands within each row are sorted by X-coordinate."""
        rows = group_bands_into_rows(sample_bands)

        for row in rows:
            x_coords = [band['center']['x'] for band in row['bands']]
            assert x_coords == sorted(x_coords)

    def test_row_bounding_box(self, sample_bands):
        """Test that row bbox encompasses all bands."""
        rows = group_bands_into_rows(sample_bands)

        # First row bands span x: 20-280, y: 30-70
        row1 = rows[0]
        assert row1['bbox']['x1'] == 20
        assert row1['bbox']['x2'] == 280
        assert row1['bbox']['y1'] == 30
        assert row1['bbox']['y2'] == 70

    def test_empty_input_returns_empty(self):
        """Test that empty input returns empty list."""
        rows = group_bands_into_rows([])
        assert rows == []

    def test_single_band_creates_single_row(self):
        """Test that a single band creates a single row."""
        single_band = [{
            'id': 0,
            'bbox': {'x1': 10, 'y1': 20, 'x2': 50, 'y2': 60},
            'confidence': 0.9,
            'center': {'x': 30.0, 'y': 40.0},
            'width': 40,
            'height': 40,
        }]
        rows = group_bands_into_rows(single_band)

        assert len(rows) == 1
        assert rows[0]['band_count'] == 1

    def test_custom_y_tolerance(self, sample_bands):
        """Test grouping with custom Y-tolerance."""
        # Very small tolerance should create more rows
        rows_small = group_bands_into_rows(sample_bands, y_tolerance=5)
        # Very large tolerance should create fewer rows
        rows_large = group_bands_into_rows(sample_bands, y_tolerance=200)

        assert len(rows_small) == 2  # Still 2, bands in same row are close
        assert len(rows_large) == 1  # All bands in one row

    def test_band_ids_reassigned_within_rows(self, sample_bands):
        """Test that band IDs are reassigned 0, 1, 2... within each row."""
        rows = group_bands_into_rows(sample_bands)

        for row in rows:
            ids = [band['id'] for band in row['bands']]
            assert ids == list(range(len(ids)))

    def test_row_ids_sequential(self, sample_bands):
        """Test that row IDs are sequential starting from 0."""
        rows = group_bands_into_rows(sample_bands)

        row_ids = [row['row_id'] for row in rows]
        assert row_ids == list(range(len(rows)))

    def test_bands_at_same_y_grouped_together(self):
        """Test that bands at same Y are grouped regardless of input order."""
        # Bands intentionally in wrong order
        shuffled_bands = [
            {'id': 0, 'bbox': {'x1': 100, 'y1': 100, 'x2': 150, 'y2': 140},
             'confidence': 0.9, 'center': {'x': 125.0, 'y': 120.0}, 'width': 50, 'height': 40},
            {'id': 1, 'bbox': {'x1': 0, 'y1': 0, 'x2': 50, 'y2': 40},
             'confidence': 0.9, 'center': {'x': 25.0, 'y': 20.0}, 'width': 50, 'height': 40},
            {'id': 2, 'bbox': {'x1': 200, 'y1': 100, 'x2': 250, 'y2': 140},
             'confidence': 0.9, 'center': {'x': 225.0, 'y': 120.0}, 'width': 50, 'height': 40},
            {'id': 3, 'bbox': {'x1': 100, 'y1': 0, 'x2': 150, 'y2': 40},
             'confidence': 0.9, 'center': {'x': 125.0, 'y': 20.0}, 'width': 50, 'height': 40},
        ]

        rows = group_bands_into_rows(shuffled_bands)

        assert len(rows) == 2
        # Top row (y~20) should have 2 bands
        assert rows[0]['band_count'] == 2
        assert rows[0]['y_center'] == pytest.approx(20.0, abs=1)
        # Bottom row (y~120) should have 2 bands
        assert rows[1]['band_count'] == 2
        assert rows[1]['y_center'] == pytest.approx(120.0, abs=1)
