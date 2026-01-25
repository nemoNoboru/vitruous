import os
from pathlib import Path

from flask import Flask


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    # Default configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        UPLOAD_FOLDER=os.path.join(app.root_path, 'static/uploads'),
        MODEL_PATH=os.environ.get('MODEL_PATH', 'output/best_model.pt'),
        MODEL_DEVICE=os.environ.get('MODEL_DEVICE', 'auto'),
    )

    if test_config is None:
        # Load instance config if it exists
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    # Ensure upload folder exists
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'])
    except OSError:
        pass

    # Initialize the ML model
    with app.app_context():
        _initialize_model(app)

    # Register blueprints
    from . import routes
    app.register_blueprint(routes.bp)

    return app


def _initialize_model(app: Flask) -> None:
    """Initialize the band detection model at startup."""
    from app.services.model_manager import get_model_manager

    model_path = app.config['MODEL_PATH']
    device = app.config['MODEL_DEVICE']

    # Resolve relative path from project root
    if not os.path.isabs(model_path):
        project_root = Path(app.root_path).parent
        model_path = str(project_root / model_path)

    if os.path.exists(model_path):
        try:
            get_model_manager().initialize(model_path, device)
            app.logger.info(f"Model loaded from {model_path}")
        except Exception as e:
            app.logger.error(f"Failed to load model: {e}")
    else:
        app.logger.warning(f"Model file not found at {model_path}")
