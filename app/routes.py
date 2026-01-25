import os

from flask import Blueprint, render_template, request, jsonify, current_app
from werkzeug.utils import secure_filename

from app.services.orchestrator import detect_blot, analyze_row
from app.services.model_manager import get_model_manager


bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/detect', methods=['POST'])
def detect():
    """Detect bands in an image and group them into rows."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    filename = data.get('filename')
    if not filename:
        return jsonify({'error': 'No filename provided'}), 400

    # Security check
    filename = secure_filename(filename)
    confidence = data.get('confidence', 0.5)

    filepath = os.path.join(current_app.root_path, 'static/demo_images', filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'Image not found'}), 404

    try:
        results = detect_blot(filepath, confidence_threshold=confidence)
        results['original'] = f"/static/demo_images/{filename}"
        return jsonify(results)
    except Exception as e:
        current_app.logger.error(f"Detection failed: {e}")
        return jsonify({'error': 'Detection failed'}), 500


@bp.route('/analyze-row', methods=['POST'])
def analyze_row_endpoint():
    """Analyze intensities for a specific row."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    filename = data.get('filename')
    row_id = data.get('row_id')

    if not filename:
        return jsonify({'error': 'No filename provided'}), 400
    if row_id is None:
        return jsonify({'error': 'No row_id provided'}), 400

    # Security check
    filename = secure_filename(filename)

    filepath = os.path.join(current_app.root_path, 'static/demo_images', filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'Image not found'}), 404

    try:
        results = analyze_row(filepath, row_id=int(row_id))
        if results is None:
            return jsonify({'error': f'Row {row_id} not found'}), 404
        return jsonify(results)
    except Exception as e:
        current_app.logger.error(f"Row analysis failed: {e}")
        return jsonify({'error': 'Analysis failed'}), 500


@bp.route('/model-info')
def model_info():
    """Return model status and information."""
    manager = get_model_manager()
    return jsonify(manager.get_info())


@bp.route('/demo-images')
def get_demo_images():
    """List available demo images."""
    demo_dir = os.path.join(current_app.root_path, 'static/demo_images')
    if not os.path.exists(demo_dir):
        return jsonify([])

    images = [f for f in os.listdir(demo_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    return jsonify(sorted(images))
