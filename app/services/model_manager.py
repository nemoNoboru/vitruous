"""
Singleton Model Manager for Western Blot Band Detection

Thread-safe singleton pattern for loading the Faster R-CNN model once at startup.
"""

import json
import threading
from pathlib import Path
from typing import Optional

import torch
from torchvision import transforms as T


class ModelManager:
    """Thread-safe singleton for managing the detection model."""

    _instance: Optional['ModelManager'] = None
    _lock = threading.Lock()

    def __new__(cls) -> 'ModelManager':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        assert cls._instance is not None  # Type narrowing for mypy/ty
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.model = None
        self.device = None
        self.model_type = None
        self.transform = T.ToTensor()
        self._initialized = True

    def initialize(self, model_path: str, device: str = 'auto') -> None:
        """
        Load the model from disk.

        Args:
            model_path: Path to the .pt model file
            device: 'auto', 'cuda', or 'cpu'
        """
        if self.model is not None:
            return  # Already initialized

        if device == 'auto':
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device

        model_dir = Path(model_path).parent
        info_path = model_dir / 'model_info.json'

        if info_path.exists():
            with open(info_path) as f:
                info = json.load(f)
                self.model_type = info.get('model_type', 'fasterrcnn')
        else:
            self.model_type = 'fasterrcnn'

        self.model = self._build_model(self.model_type, num_classes=2)
        self.model.load_state_dict(torch.load(model_path, map_location=self.device, weights_only=True))
        self.model.to(self.device)
        self.model.eval()

    def _build_model(self, model_type: str, num_classes: int = 2):
        """Build model architecture based on type."""

        if model_type == 'ssd':
            from torchvision.models.detection import ssdlite320_mobilenet_v3_large
            from torchvision.models.detection.ssd import SSDClassificationHead
            model = ssdlite320_mobilenet_v3_large(weights=None)
            in_channels = [672, 480, 512, 256, 256, 128]
            num_anchors = [6, 6, 6, 6, 6, 6]
            model.head.classification_head = SSDClassificationHead(
                in_channels, num_anchors, num_classes
            )
            return model

        elif model_type == 'fasterrcnn_mobilenet':
            from torchvision.models.detection import fasterrcnn_mobilenet_v3_large_fpn
            from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
            model = fasterrcnn_mobilenet_v3_large_fpn(weights=None)
            in_features = model.roi_heads.box_predictor.cls_score.in_features
            model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
            return model

        elif model_type == 'fasterrcnn':
            from torchvision.models.detection import fasterrcnn_resnet50_fpn
            from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
            model = fasterrcnn_resnet50_fpn(weights=None)
            in_features = model.roi_heads.box_predictor.cls_score.in_features
            model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
            return model

        else:
            raise ValueError(f"Unknown model type: {model_type}")

    def predict(self, image_tensor: torch.Tensor) -> dict:
        """
        Run inference on an image tensor.

        Args:
            image_tensor: Tensor of shape (C, H, W) or (1, C, H, W)

        Returns:
            Dict with 'boxes', 'scores', 'labels' tensors
        """
        if self.model is None:
            raise RuntimeError("Model not initialized. Call initialize() first.")

        if image_tensor.dim() == 3:
            image_tensor = image_tensor.unsqueeze(0)

        image_tensor = image_tensor.to(self.device)

        with torch.no_grad():
            predictions = self.model(image_tensor)[0]

        return predictions

    def get_info(self) -> dict:
        """Return model status information."""
        return {
            'initialized': self.model is not None,
            'model_type': self.model_type,
            'device': str(self.device) if self.device else None,
        }


def get_model_manager() -> ModelManager:
    """Get the singleton ModelManager instance."""
    return ModelManager()
