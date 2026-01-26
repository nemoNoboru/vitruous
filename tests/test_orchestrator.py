"""
Tests for the orchestrator service with mocked dependencies.
"""

from unittest.mock import patch

from app.services.orchestrator import (
    _detection_cache,
    analyze_row,
    analyze_row_with_custom_bboxes,
    clear_cache,
    detect_blot,
)


class TestDetectBlot:
    """Test the detect_blot orchestration function."""

    def test_returns_detection_result(self, sample_image_path, mock_model_manager):
        """Test that detect_blot returns proper structure."""
        with patch('app.services.band_detection.get_model_manager', return_value=mock_model_manager):
            result = detect_blot(sample_image_path)

        assert 'width' in result
        assert 'height' in result
        assert 'rows' in result
        assert 'total_bands' in result
        assert 'total_rows' in result

    def test_groups_bands_into_rows(self, sample_image_path, mock_model_manager):
        """Test that bands are grouped into rows."""
        with patch('app.services.band_detection.get_model_manager', return_value=mock_model_manager):
            result = detect_blot(sample_image_path)

        # Mock returns 6 bands in 2 rows
        assert result['total_rows'] == 2
        assert result['total_bands'] == 6

    def test_caches_results_for_subsequent_calls(self, sample_image_path, mock_model_manager):
        """Test that results are cached for subsequent analyze_row calls."""
        clear_cache()

        with patch('app.services.band_detection.get_model_manager', return_value=mock_model_manager):
            # First call should detect and cache
            detect_blot(sample_image_path)
            # Second call to analyze_row should use cache (model not called again)
            result = analyze_row(sample_image_path, row_id=0)

        assert result is not None
        # Model predict was called only once during detect_blot
        assert mock_model_manager.predict.call_count == 1

    def test_respects_confidence_threshold(self, sample_image_path, mock_model_manager):
        """Test that confidence threshold is passed to detection."""
        with patch('app.services.band_detection.get_model_manager', return_value=mock_model_manager):
            # High threshold should filter out bands
            result = detect_blot(sample_image_path, confidence_threshold=0.93)

        # Only 1 band has confidence >= 0.93 (the 0.95 one)
        assert result['total_bands'] == 1


class TestAnalyzeRow:
    """Test the analyze_row function."""

    def test_analyzes_valid_row(self, sample_image_path, mock_model_manager):
        """Test that valid row ID returns analysis results."""
        clear_cache()

        with patch('app.services.band_detection.get_model_manager', return_value=mock_model_manager):
            detect_blot(sample_image_path)
            result = analyze_row(sample_image_path, row_id=0)

        assert result is not None
        assert result['row_id'] == 0
        assert 'bands' in result
        assert 'profile' in result

    def test_returns_none_for_invalid_row(self, sample_image_path, mock_model_manager):
        """Test that invalid row ID returns None."""
        clear_cache()

        with patch('app.services.band_detection.get_model_manager', return_value=mock_model_manager):
            detect_blot(sample_image_path)
            result = analyze_row(sample_image_path, row_id=999)

        assert result is None

    def test_redetects_if_not_cached(self, sample_image_path, mock_model_manager):
        """Test that analyze_row triggers detection if not cached."""
        clear_cache()

        with patch('app.services.band_detection.get_model_manager', return_value=mock_model_manager):
            # Call analyze_row without prior detect_blot
            result = analyze_row(sample_image_path, row_id=0)

        assert result is not None
        # Model was called to do detection
        assert mock_model_manager.predict.call_count >= 1

    def test_returns_intensity_metrics(self, sample_image_path, mock_model_manager):
        """Test that analysis includes intensity metrics."""
        clear_cache()

        with patch('app.services.band_detection.get_model_manager', return_value=mock_model_manager):
            detect_blot(sample_image_path)
            result = analyze_row(sample_image_path, row_id=0)

        bands = result['bands']
        assert len(bands) > 0
        for band in bands:
            assert 'intensity' in band
            assert 'integrated_density' in band['intensity']
            assert 'relative' in band['intensity']

    def test_returns_profile(self, sample_image_path, mock_model_manager):
        """Test that analysis includes densitometry profile."""
        clear_cache()

        with patch('app.services.band_detection.get_model_manager', return_value=mock_model_manager):
            detect_blot(sample_image_path)
            result = analyze_row(sample_image_path, row_id=0)

        profile = result['profile']
        assert 'values' in profile
        assert 'stats' in profile


class TestAnalyzeRowWithCustomBboxes:
    """Test custom bbox analysis."""

    def test_uses_custom_bboxes(self, sample_image_path, mock_model_manager):
        """Test that custom bboxes are used for intensity calculation."""
        clear_cache()

        custom_bboxes = [
            {'x1': 10, 'y1': 20, 'x2': 50, 'y2': 60},
            {'x1': 100, 'y1': 20, 'x2': 140, 'y2': 60},
        ]

        with patch('app.services.band_detection.get_model_manager', return_value=mock_model_manager):
            detect_blot(sample_image_path)
            result = analyze_row_with_custom_bboxes(
                sample_image_path,
                row_id=0,
                custom_bboxes=custom_bboxes
            )

        assert result is not None
        assert len(result['bands']) == 2

        # Verify custom bboxes are used
        assert result['bands'][0]['bbox']['x1'] == 10
        assert result['bands'][1]['bbox']['x1'] == 100

    def test_returns_none_for_invalid_row(self, sample_image_path, mock_model_manager):
        """Test that invalid row returns None even with custom bboxes."""
        clear_cache()

        with patch('app.services.band_detection.get_model_manager', return_value=mock_model_manager):
            detect_blot(sample_image_path)
            result = analyze_row_with_custom_bboxes(
                sample_image_path,
                row_id=999,
                custom_bboxes=[{'x1': 0, 'y1': 0, 'x2': 10, 'y2': 10}]
            )

        assert result is None


class TestClearCache:
    """Test cache management."""

    def test_clear_all_cache(self, sample_image_path, mock_model_manager):
        """Test clearing entire cache."""
        with patch('app.services.band_detection.get_model_manager', return_value=mock_model_manager):
            detect_blot(sample_image_path)
            # Verify something is cached by checking analyze_row works
            result_before = analyze_row(sample_image_path, row_id=0)
            assert result_before is not None

            clear_cache()

            # After clearing, analyze_row needs to re-detect (predict called again)
            call_count_before = mock_model_manager.predict.call_count
            analyze_row(sample_image_path, row_id=0)
            assert mock_model_manager.predict.call_count > call_count_before

    def test_clear_specific_image(self, sample_image_path, mock_model_manager):
        """Test clearing specific image from cache."""
        with patch('app.services.band_detection.get_model_manager', return_value=mock_model_manager):
            detect_blot(sample_image_path)

        clear_cache(sample_image_path)

        assert sample_image_path not in _detection_cache

    def test_clear_nonexistent_image(self):
        """Test that clearing non-existent image doesn't raise."""
        clear_cache('/nonexistent/path.png')  # Should not raise
