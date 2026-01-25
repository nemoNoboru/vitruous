"""
Band Detection Service

Uses the Faster R-CNN model to detect bands in western blot images.
"""

from typing import TypedDict

from PIL import Image
from torchvision import transforms as T

from app.services.model_manager import get_model_manager


class BBox(TypedDict):
    x1: int
    y1: int
    x2: int
    y2: int


class Center(TypedDict):
    x: float
    y: float


class DetectedBand(TypedDict):
    id: int
    bbox: BBox
    confidence: float
    center: Center
    width: int
    height: int


def detect_bands(image_path: str, confidence_threshold: float = 0.5) -> list[DetectedBand]:
    """
    Detect bands in a western blot image.

    Args:
        image_path: Path to the image file
        confidence_threshold: Minimum confidence score to include a detection

    Returns:
        List of detected bands with bounding boxes, confidence, and center coordinates
    """
    model_manager = get_model_manager()
    transform = T.ToTensor()

    image = Image.open(image_path).convert('RGB')
    image_tensor = transform(image)

    predictions = model_manager.predict(image_tensor)

    boxes = predictions['boxes'].cpu().numpy()
    scores = predictions['scores'].cpu().numpy()

    bands: list[DetectedBand] = []

    for i, (box, score) in enumerate(zip(boxes, scores)):
        if score < confidence_threshold:
            continue

        x1, y1, x2, y2 = box.astype(int)
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        width = x2 - x1
        height = y2 - y1

        bands.append({
            'id': i,
            'bbox': {'x1': int(x1), 'y1': int(y1), 'x2': int(x2), 'y2': int(y2)},
            'confidence': float(score),
            'center': {'x': float(center_x), 'y': float(center_y)},
            'width': int(width),
            'height': int(height),
        })

    # Re-assign IDs after filtering to ensure contiguous numbering
    for i, band in enumerate(bands):
        band['id'] = i

    return bands
