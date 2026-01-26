import os

from flask import Blueprint, current_app, jsonify, render_template, request
from werkzeug.utils import secure_filename

from app.services.model_manager import get_model_manager
from app.services.orchestrator import analyze_row, analyze_row_with_custom_bboxes, detect_blot

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    return render_template('index.html')


def find_image_path(filename):
    """Find image in demo_images or uploads directory."""
    filename = secure_filename(filename)

    # Check demo_images first
    demo_path = os.path.join(current_app.root_path, 'static/demo_images', filename)
    if os.path.exists(demo_path):
        return demo_path, f"/static/demo_images/{filename}"

    # Check uploads
    upload_path = os.path.join(current_app.root_path, 'static/uploads', filename)
    if os.path.exists(upload_path):
        return upload_path, f"/static/uploads/{filename}"

    return None, None


@bp.route('/detect', methods=['POST'])
def detect():
    """Detect bands in an image and group them into rows."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    filename = data.get('filename')
    if not filename:
        return jsonify({'error': 'No filename provided'}), 400

    confidence = data.get('confidence', 0.5)

    filepath, web_path = find_image_path(filename)
    if not filepath:
        return jsonify({'error': 'Image not found'}), 404

    try:
        results = detect_blot(filepath, confidence_threshold=confidence)
        results['original'] = web_path
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

    filepath, _ = find_image_path(filename)
    if not filepath:
        return jsonify({'error': 'Image not found'}), 404

    try:
        results = analyze_row(filepath, row_id=int(row_id))
        if results is None:
            return jsonify({'error': f'Row {row_id} not found'}), 404
        return jsonify(results)
    except Exception as e:
        current_app.logger.error(f"Row analysis failed: {e}")
        return jsonify({'error': 'Analysis failed'}), 500


@bp.route('/analyze-row-custom', methods=['POST'])
def analyze_row_custom_endpoint():
    """Analyze a row using custom band boundaries."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    filename = data.get('filename')
    row_id = data.get('row_id')
    custom_bboxes = data.get('bboxes')

    if not filename:
        return jsonify({'error': 'No filename provided'}), 400
    if row_id is None:
        return jsonify({'error': 'No row_id provided'}), 400
    if not custom_bboxes:
        return jsonify({'error': 'No bboxes provided'}), 400

    filepath, _ = find_image_path(filename)
    if not filepath:
        return jsonify({'error': 'Image not found'}), 404

    try:
        results = analyze_row_with_custom_bboxes(
            filepath,
            row_id=int(row_id),
            custom_bboxes=custom_bboxes
        )
        if results is None:
            return jsonify({'error': f'Row {row_id} not found'}), 404
        return jsonify(results)
    except Exception as e:
        current_app.logger.error(f"Custom row analysis failed: {e}")
        return jsonify({'error': 'Analysis failed'}), 500


@bp.route('/model-info')
def model_info():
    """Return model status and information."""
    manager = get_model_manager()
    return jsonify(manager.get_info())


@bp.route('/upload', methods=['POST'])
def upload_image():
    """Upload an image file for analysis."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    if not file.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
        return jsonify({'error': 'Invalid file type'}), 400

    filename = secure_filename(file.filename)
    upload_dir = os.path.join(current_app.root_path, 'static/uploads')
    os.makedirs(upload_dir, exist_ok=True)

    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    return jsonify({
        'filename': filename,
        'path': f'/static/uploads/{filename}'
    })


@bp.route('/demo-images')
def get_demo_images():
    """List available demo images."""
    demo_dir = os.path.join(current_app.root_path, 'static/demo_images')
    if not os.path.exists(demo_dir):
        return jsonify([])

    images = [f for f in os.listdir(demo_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    return jsonify(sorted(images))
