"""
Test fixtures for Western Blot Band Detection app.
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch
from PIL import Image

from app import create_app
from app.services.band_detection import DetectedBand


@pytest.fixture
def mock_model_manager():
    """
    Mock ModelManager that returns predictable predictions.
    Returns 6 bands arranged in 2 rows of 3.
    """
    mock = MagicMock()
    mock.model = MagicMock()  # Model is "initialized"
    mock.device = 'cpu'
    mock.model_type = 'fasterrcnn'

    # Predict returns 6 bands in 2 rows (y=50 and y=150)
    # Row 1: x centers at 50, 150, 250 (y=50)
    # Row 2: x centers at 50, 150, 250 (y=150)
    boxes = torch.tensor([
        [20, 30, 80, 70],    # Row 1, Band 1
        [120, 30, 180, 70],  # Row 1, Band 2
        [220, 30, 280, 70],  # Row 1, Band 3
        [20, 130, 80, 170],  # Row 2, Band 1
        [120, 130, 180, 170],  # Row 2, Band 2
        [220, 130, 280, 170],  # Row 2, Band 3
    ], dtype=torch.float32)
    scores = torch.tensor([0.95, 0.92, 0.89, 0.88, 0.91, 0.87], dtype=torch.float32)
    labels = torch.tensor([1, 1, 1, 1, 1, 1], dtype=torch.int64)

    mock.predict.return_value = {
        'boxes': boxes,
        'scores': scores,
        'labels': labels,
    }

    mock.get_info.return_value = {
        'initialized': True,
        'model_type': 'fasterrcnn',
        'device': 'cpu',
    }

    return mock


@pytest.fixture
def app(mock_model_manager):
    """Flask test app with mocked model initialization."""
    with patch('app.services.model_manager.ModelManager') as MockClass:
        # Make the singleton return our mock
        MockClass.return_value = mock_model_manager

        with patch('app.services.band_detection.get_model_manager', return_value=mock_model_manager):
            test_app = create_app({
                'TESTING': True,
                'UPLOAD_FOLDER': tempfile.mkdtemp(),
                'MODEL_PATH': '/tmp/fake_model.pt',
            })
            yield test_app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def sample_grayscale_image() -> np.ndarray:
    """
    Synthetic 200x400 grayscale blot image with dark bands.
    White background (255) with dark bands (~50 intensity).
    """
    # Start with white background
    img = np.full((200, 400, 1), 255, dtype=np.uint8)

    # Add dark bands (simulating protein bands)
    # Row 1 (y: 30-70)
    img[30:70, 20:80] = 50      # Band 1
    img[30:70, 120:180] = 80    # Band 2 (lighter)
    img[30:70, 220:280] = 30    # Band 3 (darker)

    # Row 2 (y: 130-170)
    img[130:170, 20:80] = 60    # Band 4
    img[130:170, 120:180] = 40  # Band 5
    img[130:170, 220:280] = 70  # Band 6

    return img.squeeze()  # Return as 2D grayscale


@pytest.fixture
def sample_rgb_image(sample_grayscale_image) -> np.ndarray:
    """RGB version of the sample image."""
    return np.stack([sample_grayscale_image] * 3, axis=-1)


@pytest.fixture
def sample_image_path(sample_grayscale_image, tmp_path) -> str:
    """Save sample image to a temp file and return the path."""
    img_path = tmp_path / "test_blot.png"
    Image.fromarray(sample_grayscale_image).save(img_path)
    return str(img_path)


@pytest.fixture
def sample_bands() -> list[DetectedBand]:
    """
    List of 6 DetectedBand dicts (2 rows of 3).
    Matches the coordinates used in sample_grayscale_image.
    """
    return [
        {
            'id': 0,
            'bbox': {'x1': 20, 'y1': 30, 'x2': 80, 'y2': 70},
            'confidence': 0.95,
            'center': {'x': 50.0, 'y': 50.0},
            'width': 60,
            'height': 40,
        },
        {
            'id': 1,
            'bbox': {'x1': 120, 'y1': 30, 'x2': 180, 'y2': 70},
            'confidence': 0.92,
            'center': {'x': 150.0, 'y': 50.0},
            'width': 60,
            'height': 40,
        },
        {
            'id': 2,
            'bbox': {'x1': 220, 'y1': 30, 'x2': 280, 'y2': 70},
            'confidence': 0.89,
            'center': {'x': 250.0, 'y': 50.0},
            'width': 60,
            'height': 40,
        },
        {
            'id': 3,
            'bbox': {'x1': 20, 'y1': 130, 'x2': 80, 'y2': 170},
            'confidence': 0.88,
            'center': {'x': 50.0, 'y': 150.0},
            'width': 60,
            'height': 40,
        },
        {
            'id': 4,
            'bbox': {'x1': 120, 'y1': 130, 'x2': 180, 'y2': 170},
            'confidence': 0.91,
            'center': {'x': 150.0, 'y': 150.0},
            'width': 60,
            'height': 40,
        },
        {
            'id': 5,
            'bbox': {'x1': 220, 'y1': 130, 'x2': 280, 'y2': 170},
            'confidence': 0.87,
            'center': {'x': 250.0, 'y': 150.0},
            'width': 60,
            'height': 40,
        },
    ]


@pytest.fixture
def demo_image_setup(app, sample_grayscale_image):
    """Set up a demo image in the app's static directory."""
    demo_dir = os.path.join(app.root_path, 'static/demo_images')
    os.makedirs(demo_dir, exist_ok=True)

    img_path = os.path.join(demo_dir, 'test_demo.png')
    Image.fromarray(sample_grayscale_image).save(img_path)

    yield 'test_demo.png'

    # Cleanup
    if os.path.exists(img_path):
        os.remove(img_path)
