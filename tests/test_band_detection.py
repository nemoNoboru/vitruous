"""
Tests for band detection with mocked YOLO model.
"""

from unittest.mock import patch

from app.services.band_detection import detect_bands


class TestDetectBands:
    """Test band detection with mocked model."""

    def test_detects_bands_above_threshold(self, sample_image_path, mock_model_manager):
        """Test that bands above confidence threshold are returned."""
        with patch('app.services.band_detection.get_model_manager', return_value=mock_model_manager):
            bands = detect_bands(sample_image_path, confidence_threshold=0.5)

        assert len(bands) == 6
        for band in bands:
            assert band['confidence'] >= 0.5

    def test_filters_low_confidence_bands(self, sample_image_path, mock_model_manager):
        """Test that bands below threshold are filtered out."""
        with patch('app.services.band_detection.get_model_manager', return_value=mock_model_manager):
            # Set threshold higher than some predictions
            bands = detect_bands(sample_image_path, confidence_threshold=0.9)

        # Only bands with score >= 0.9 should be included
        # Our mock has scores: [0.95, 0.92, 0.89, 0.88, 0.91, 0.87]
        assert len(bands) == 3
        for band in bands:
            assert band['confidence'] >= 0.9

    def test_band_structure(self, sample_image_path, mock_model_manager):
        """Test that detected bands have correct structure."""
        with patch('app.services.band_detection.get_model_manager', return_value=mock_model_manager):
            bands = detect_bands(sample_image_path, confidence_threshold=0.5)

        band = bands[0]
        assert 'id' in band
        assert 'bbox' in band
        assert 'confidence' in band
        assert 'center' in band
        assert 'width' in band
        assert 'height' in band

        # Check bbox structure
        assert 'x1' in band['bbox']
        assert 'y1' in band['bbox']
        assert 'x2' in band['bbox']
        assert 'y2' in band['bbox']

        # Check center structure
        assert 'x' in band['center']
        assert 'y' in band['center']

    def test_band_ids_are_contiguous(self, sample_image_path, mock_model_manager):
        """Test that band IDs are reassigned to be contiguous after filtering."""
        with patch('app.services.band_detection.get_model_manager', return_value=mock_model_manager):
            bands = detect_bands(sample_image_path, confidence_threshold=0.9)

        ids = [band['id'] for band in bands]
        assert ids == list(range(len(bands)))

    def test_center_calculation(self, sample_image_path, mock_model_manager):
        """Test that center is correctly calculated from bbox."""
        with patch('app.services.band_detection.get_model_manager', return_value=mock_model_manager):
            bands = detect_bands(sample_image_path, confidence_threshold=0.5)

        band = bands[0]
        expected_center_x = (band['bbox']['x1'] + band['bbox']['x2']) / 2
        expected_center_y = (band['bbox']['y1'] + band['bbox']['y2']) / 2

        assert band['center']['x'] == expected_center_x
        assert band['center']['y'] == expected_center_y

    def test_width_height_calculation(self, sample_image_path, mock_model_manager):
        """Test that width and height are correctly calculated."""
        with patch('app.services.band_detection.get_model_manager', return_value=mock_model_manager):
            bands = detect_bands(sample_image_path, confidence_threshold=0.5)

        band = bands[0]
        expected_width = band['bbox']['x2'] - band['bbox']['x1']
        expected_height = band['bbox']['y2'] - band['bbox']['y1']

        assert band['width'] == expected_width
        assert band['height'] == expected_height

    def test_no_bands_above_threshold(self, sample_image_path, mock_model_manager):
        """Test handling when no bands meet threshold."""
        with patch('app.services.band_detection.get_model_manager', return_value=mock_model_manager):
            bands = detect_bands(sample_image_path, confidence_threshold=0.99)

        assert bands == []

    def test_default_confidence_threshold(self, sample_image_path, mock_model_manager):
        """Test that default threshold of 0.5 is used."""
        with patch('app.services.band_detection.get_model_manager', return_value=mock_model_manager):
            bands = detect_bands(sample_image_path)

        # All mock bands have confidence > 0.5
        assert len(bands) == 6
