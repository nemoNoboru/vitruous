"""
Tests for densitometry calculations.
Pure unit tests - no model needed.
"""


from app.services.densitometry import (
    calculate_all_band_intensities,
    calculate_band_intensity,
    calculate_profile,
)


class TestCalculateBandIntensity:
    """Test single band intensity calculations."""

    def test_basic_intensity_calculation(self, sample_grayscale_image, sample_bands):
        """Test that intensity is calculated for a valid band."""
        band = sample_bands[0]  # First band at (20,30)-(80,70)
        metrics = calculate_band_intensity(sample_grayscale_image, band)

        # Verify all expected keys are present
        assert 'total' in metrics
        assert 'mean' in metrics
        assert 'max' in metrics
        assert 'min' in metrics
        assert 'integrated_density' in metrics
        assert 'background' in metrics
        assert 'background_corrected' in metrics
        assert 'relative' in metrics

        # Values should be positive (inverted from dark bands)
        assert metrics['total'] > 0
        assert metrics['mean'] > 0

    def test_dark_band_has_high_intensity(self, sample_grayscale_image, sample_bands):
        """Darker bands should have higher inverted intensity."""
        # Band 3 (index 2) has intensity 30 (darkest in row 1)
        # Band 2 (index 1) has intensity 80 (lightest in row 1)
        dark_band = sample_bands[2]
        light_band = sample_bands[1]

        dark_metrics = calculate_band_intensity(sample_grayscale_image, dark_band)
        light_metrics = calculate_band_intensity(sample_grayscale_image, light_band)

        # After inversion: darker original = higher intensity value
        assert dark_metrics['mean'] > light_metrics['mean']

    def test_empty_region_returns_zeros(self, sample_grayscale_image):
        """Test handling of invalid/empty region."""
        invalid_band = {
            'id': 0,
            'bbox': {'x1': 500, 'y1': 500, 'x2': 500, 'y2': 500},  # Out of bounds
            'confidence': 0.9,
            'center': {'x': 500, 'y': 500},
            'width': 0,
            'height': 0,
        }
        metrics = calculate_band_intensity(sample_grayscale_image, invalid_band)

        assert metrics['total'] == 0.0
        assert metrics['mean'] == 0.0

    def test_boundary_clamping(self, sample_grayscale_image):
        """Test that coordinates are properly clamped to image bounds."""
        # Band that extends beyond image boundaries
        edge_band = {
            'id': 0,
            'bbox': {'x1': -10, 'y1': -10, 'x2': 50, 'y2': 50},
            'confidence': 0.9,
            'center': {'x': 20, 'y': 20},
            'width': 60,
            'height': 60,
        }
        # Should not raise an error
        metrics = calculate_band_intensity(sample_grayscale_image, edge_band)
        assert metrics['total'] >= 0


class TestCalculateAllBandIntensities:
    """Test batch intensity calculation with normalization."""

    def test_calculates_all_bands(self, sample_image_path, sample_bands):
        """Test that all bands are processed."""
        # Use first 3 bands (row 1 only)
        bands = sample_bands[:3]
        results = calculate_all_band_intensities(sample_image_path, bands)

        assert len(results) == 3
        for result in results:
            assert 'id' in result
            assert 'bbox' in result
            assert 'intensity' in result

    def test_relative_normalization(self, sample_image_path, sample_bands):
        """Test that relative values are normalized to max."""
        bands = sample_bands[:3]
        results = calculate_all_band_intensities(sample_image_path, bands)

        # Find the max intensity band
        max_relative = max(r['intensity']['relative'] for r in results)
        assert max_relative == 1.0  # Max should be normalized to 1.0

        # All relative values should be between 0 and 1
        for result in results:
            assert 0 <= result['intensity']['relative'] <= 1.0

    def test_empty_band_list(self, sample_image_path):
        """Test handling of empty band list."""
        results = calculate_all_band_intensities(sample_image_path, [])
        assert results == []


class TestCalculateProfile:
    """Test densitometry profile calculations."""

    def test_profile_calculation(self, sample_image_path):
        """Test column-wise profile calculation."""
        region = {'x1': 20, 'y1': 30, 'x2': 80, 'y2': 70}
        profile = calculate_profile(sample_image_path, region)

        assert 'values' in profile
        assert 'stats' in profile
        assert len(profile['values']) == 60  # x2 - x1 = 60 columns
        assert 'min' in profile['stats']
        assert 'max' in profile['stats']
        assert 'mean' in profile['stats']
        assert 'std' in profile['stats']

    def test_profile_values_are_inverted(self, sample_image_path):
        """Test that profile values are inverted (dark = high)."""
        # Band 3 region (darkest, intensity 30)
        region = {'x1': 220, 'y1': 30, 'x2': 280, 'y2': 70}
        profile = calculate_profile(sample_image_path, region)

        # After inversion, 255 - 30 = 225 should be the mean (approximately)
        assert profile['stats']['mean'] > 200

    def test_empty_region_returns_empty_profile(self, sample_image_path):
        """Test handling of invalid region."""
        region = {'x1': 500, 'y1': 500, 'x2': 500, 'y2': 500}
        profile = calculate_profile(sample_image_path, region)

        assert profile['values'] == []
        assert profile['stats']['min'] == 0
