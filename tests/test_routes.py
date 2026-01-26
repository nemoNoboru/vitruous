"""
Tests for Flask API routes.
"""

import io
from unittest.mock import patch

from PIL import Image


class TestIndexRoute:
    """Test the main index page."""

    def test_index_returns_200(self, client):
        """Test that index page loads successfully."""
        response = client.get('/')
        assert response.status_code == 200

    def test_index_returns_html(self, client):
        """Test that index returns HTML content."""
        response = client.get('/')
        assert b'<!DOCTYPE html>' in response.data or b'<html' in response.data


class TestDetectRoute:
    """Test the /detect endpoint."""

    def test_detect_requires_json(self, client):
        """Test that detect endpoint requires JSON data."""
        response = client.post('/detect')
        # Returns 400 (no JSON) or 415 (unsupported media type)
        assert response.status_code in (400, 415)

    def test_detect_requires_filename(self, client):
        """Test that detect endpoint requires filename."""
        response = client.post('/detect', json={})
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_detect_returns_404_for_missing_image(self, client):
        """Test that detect returns 404 for non-existent image."""
        response = client.post('/detect', json={'filename': 'nonexistent.png'})
        assert response.status_code == 404

    def test_detect_with_valid_image(self, client, demo_image_setup, mock_model_manager):
        """Test detection with a valid demo image."""
        with patch('app.services.band_detection.get_model_manager', return_value=mock_model_manager):
            response = client.post('/detect', json={
                'filename': demo_image_setup,
                'confidence': 0.5
            })

        assert response.status_code == 200
        data = response.get_json()
        assert 'rows' in data
        assert 'total_bands' in data
        assert 'total_rows' in data
        assert 'width' in data
        assert 'height' in data
        assert 'original' in data


class TestAnalyzeRowRoute:
    """Test the /analyze-row endpoint."""

    def test_analyze_row_requires_json(self, client):
        """Test that analyze-row requires JSON data."""
        response = client.post('/analyze-row')
        # Returns 400 (no JSON) or 415 (unsupported media type)
        assert response.status_code in (400, 415)

    def test_analyze_row_requires_filename(self, client):
        """Test that analyze-row requires filename."""
        response = client.post('/analyze-row', json={'row_id': 0})
        assert response.status_code == 400

    def test_analyze_row_requires_row_id(self, client):
        """Test that analyze-row requires row_id."""
        response = client.post('/analyze-row', json={'filename': 'test.png'})
        assert response.status_code == 400

    def test_analyze_row_with_valid_params(self, client, demo_image_setup, mock_model_manager):
        """Test row analysis with valid parameters."""
        with patch('app.services.band_detection.get_model_manager', return_value=mock_model_manager):
            # First detect to populate cache
            client.post('/detect', json={'filename': demo_image_setup})

            # Then analyze row
            response = client.post('/analyze-row', json={
                'filename': demo_image_setup,
                'row_id': 0
            })

        assert response.status_code == 200
        data = response.get_json()
        assert 'row_id' in data
        assert 'bands' in data
        assert 'profile' in data

    def test_analyze_row_invalid_row_id(self, client, demo_image_setup, mock_model_manager):
        """Test that invalid row_id returns 404."""
        with patch('app.services.band_detection.get_model_manager', return_value=mock_model_manager):
            # First detect
            client.post('/detect', json={'filename': demo_image_setup})

            # Then try invalid row
            response = client.post('/analyze-row', json={
                'filename': demo_image_setup,
                'row_id': 999
            })

        assert response.status_code == 404


class TestAnalyzeRowCustomRoute:
    """Test the /analyze-row-custom endpoint."""

    def test_analyze_row_custom_requires_bboxes(self, client):
        """Test that custom analysis requires bboxes."""
        response = client.post('/analyze-row-custom', json={
            'filename': 'test.png',
            'row_id': 0
        })
        assert response.status_code == 400

    def test_analyze_row_custom_with_valid_params(self, client, demo_image_setup, mock_model_manager):
        """Test custom row analysis with user-defined bboxes."""
        with patch('app.services.band_detection.get_model_manager', return_value=mock_model_manager):
            # First detect
            client.post('/detect', json={'filename': demo_image_setup})

            # Custom bboxes
            custom_bboxes = [
                {'x1': 25, 'y1': 35, 'x2': 75, 'y2': 65},
                {'x1': 125, 'y1': 35, 'x2': 175, 'y2': 65},
                {'x1': 225, 'y1': 35, 'x2': 275, 'y2': 65},
            ]

            response = client.post('/analyze-row-custom', json={
                'filename': demo_image_setup,
                'row_id': 0,
                'bboxes': custom_bboxes
            })

        assert response.status_code == 200
        data = response.get_json()
        assert 'bands' in data
        assert len(data['bands']) == 3


class TestModelInfoRoute:
    """Test the /model-info endpoint."""

    def test_model_info_returns_status(self, client, mock_model_manager):
        """Test that model-info returns model status."""
        with patch('app.routes.get_model_manager', return_value=mock_model_manager):
            response = client.get('/model-info')

        assert response.status_code == 200
        data = response.get_json()
        assert 'initialized' in data
        assert 'model_type' in data
        assert 'device' in data


class TestUploadRoute:
    """Test the /upload endpoint."""

    def test_upload_requires_file(self, client):
        """Test that upload requires a file."""
        response = client.post('/upload')
        assert response.status_code == 400

    def test_upload_rejects_empty_filename(self, client):
        """Test that upload rejects empty filename."""
        data = {'file': (io.BytesIO(b''), '')}
        response = client.post('/upload', data=data, content_type='multipart/form-data')
        assert response.status_code == 400

    def test_upload_rejects_invalid_extension(self, client):
        """Test that upload rejects non-image files."""
        data = {'file': (io.BytesIO(b'test content'), 'test.txt')}
        response = client.post('/upload', data=data, content_type='multipart/form-data')
        assert response.status_code == 400

    def test_upload_accepts_valid_image(self, client):
        """Test that upload accepts valid image files."""
        # Create a minimal valid PNG
        img = Image.new('RGB', (10, 10), color='white')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        data = {'file': (img_bytes, 'test_upload.png')}
        response = client.post('/upload', data=data, content_type='multipart/form-data')

        assert response.status_code == 200
        data = response.get_json()
        assert 'filename' in data
        assert 'path' in data


class TestDemoImagesRoute:
    """Test the /demo-images endpoint."""

    def test_demo_images_returns_list(self, client):
        """Test that demo-images returns a list."""
        response = client.get('/demo-images')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)

    def test_demo_images_includes_setup_image(self, client, demo_image_setup):
        """Test that demo images list includes our setup image."""
        response = client.get('/demo-images')
        data = response.get_json()
        assert demo_image_setup in data
