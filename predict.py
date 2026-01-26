"""
Inference Script for Western Blot Band Detection

Usage:
    python predict.py --model ./output/best_model.pt --image blot.png --type ssd
    python predict.py --model ./output/best_model.pt --image blot.png --type fasterrcnn_mobilenet
    python predict.py --model ./output/best_model.pt --image blot.png --type fasterrcnn
"""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image
from torchvision import transforms as T


def get_model(model_type: str, num_classes: int = 2):
    """Load model architecture."""

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
        raise ValueError(f"Unknown model: {model_type}")


def predict(
    model_path: str,
    image_path: str,
    model_type: str | None = None,
    conf_threshold: float = 0.5,
    device: str = 'auto',
    output_path: str = 'prediction.png'
):
    """Run inference."""

    if device == 'auto':
        device = 'cuda' if torch.cuda.is_available() else 'cpu'

    # Try to auto-detect model type from saved info
    model_dir = Path(model_path).parent
    info_path = model_dir / 'model_info.json'
    if model_type is None and info_path.exists():
        with open(info_path) as f:
            info = json.load(f)
            model_type = info.get('model_type', 'fasterrcnn_mobilenet')
    elif model_type is None:
        model_type = 'fasterrcnn_mobilenet'

    print(f"Using model: {model_type}")
    print(f"Device: {device}")

    # Load model
    model = get_model(model_type, num_classes=2)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.to(device)
    model.eval()

    # Load image
    image = Image.open(image_path).convert('RGB')
    transform = T.ToTensor()
    image_tensor = transform(image).unsqueeze(0).to(device)

    # Inference
    with torch.no_grad():
        predictions = model(image_tensor)[0]

    # Filter by confidence
    mask = predictions['scores'] > conf_threshold
    boxes = predictions['boxes'][mask].cpu().numpy()
    scores = predictions['scores'][mask].cpu().numpy()

    print(f"\nDetected {len(boxes)} bands (conf > {conf_threshold})")

    # Visualize
    img_np = np.array(image)
    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

    for box, score in zip(boxes, scores, strict=True):
        x1, y1, x2, y2 = box.astype(int)
        cv2.rectangle(img_bgr, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(img_bgr, f'{score:.2f}', (x1, y1-5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    cv2.imwrite(output_path, img_bgr)
    print(f"Saved: {output_path}")

    return boxes, scores


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, required=True, help='Path to model .pt file')
    parser.add_argument('--image', type=str, required=True, help='Input image')
    parser.add_argument('--type', type=str, default=None,
                        choices=['ssd', 'fasterrcnn_mobilenet', 'fasterrcnn'],
                        help='Model type (auto-detected if model_info.json exists)')
    parser.add_argument('--conf', type=float, default=0.5, help='Confidence threshold')
    parser.add_argument('--device', type=str, default='auto')
    parser.add_argument('--output', type=str, default='prediction.png')

    args = parser.parse_args()

    predict(
        model_path=args.model,
        image_path=args.image,
        model_type=args.type,
        conf_threshold=args.conf,
        device=args.device,
        output_path=args.output
    )
