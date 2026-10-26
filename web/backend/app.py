"""Flask application entry point for Siemens-Spacewise Simulator.

Initializes Flask app with CORS, registers the API blueprint,
and provides global error handlers that do not expose stack traces.
"""

import os
import sys
from pathlib import Path

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv is optional: only used to read a local .env
    def load_dotenv(*args, **kwargs):
        return False

# Add backend directory to path so queries can be imported when running from project root
_current_dir = Path(__file__).parent
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))
# Repo root too: routes import the plant package (calibration) regardless of cwd
_repo_root = _current_dir.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

# Static dashboard (HTML/CSS/JS) served by this same Flask app at "/"
FRONTEND_DIR = (_current_dir.parent / 'frontend').resolve()

load_dotenv(_current_dir / '.env')

from routes import api_bp  # noqa: E402


def _env_float(name: str, default: float) -> float:
    """Read a float env var, falling back to default on empty/garbage."""
    try:
        raw = os.getenv(name, '')
        return float(raw) if raw.strip() else default
    except (TypeError, ValueError):
        return default


def create_app(db_path: str | None = None,
               machines_dir: str | None = None) -> Flask:
    """Application factory.

    Args:
        db_path: Optional explicit database path. If None, read from
            DATABASE_PATH env var or fall back to default location.
        machines_dir: Optional explicit machines catalog directory. If None,
            use repo-root/machines (consumed by the calibration endpoint).

    Returns:
        Configured Flask application.
    """
    app = Flask(__name__, static_folder=None)

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-change-me')
    app.config['JSON_SORT_KEYS'] = False
    app.config['MACHINES_DIR'] = machines_dir or str(_repo_root / 'machines')

    # Energy assistant (Ollama) config. All optional; defaults use the local
    # Ollama server and the only model in Ollama's free plan (gemma4:cloud).
    app.config['OLLAMA_HOST'] = os.getenv('OLLAMA_HOST', 'http://127.0.0.1:11434')
    app.config['OLLAMA_MODEL'] = os.getenv('OLLAMA_MODEL', 'gemma4:cloud')
    app.config['OLLAMA_TIMEOUT'] = _env_float('OLLAMA_TIMEOUT', 120.0)
    # Price per kWh turns energy figures into money; currency is just a label.
    app.config['PRICE_KWH'] = _env_float('PRECIO_KWH', 0.0)
    app.config['CURRENCY'] = os.getenv('CURRENCY', 'USD')

    # Store database path on app config so tests can override it
    if db_path is not None:
        app.config['DATABASE_PATH'] = db_path
    else:
        env_db = os.getenv('DATABASE_PATH')
        if env_db:
            resolved = (Path(env_db) if Path(env_db).is_absolute()
                        else _current_dir / env_db).resolve()
            app.config['DATABASE_PATH'] = str(resolved)
        else:
            app.config['DATABASE_PATH'] = str(
                (_current_dir.parent.parent / 'data' / 'spacewise.db').resolve()
            )

    # Patch queries module with the configured db_path via a wrapper
    _configure_queries(app)

    # CORS: explicit origins from environment, never wildcard
    configured_origins = os.getenv('CORS_ORIGINS', '')
    origins = [o.strip() for o in configured_origins.split(',') if o.strip()]
    if not origins:
        # Safe default for local development only
        origins = ['http://localhost:8000', 'http://localhost:5500', 'http://127.0.0.1:8000',
                   'http://localhost:5000', 'http://127.0.0.1:5000']
    CORS(app, origins=origins, supports_credentials=False)

    app.register_blueprint(api_bp)

    _register_frontend(app)
    _register_error_handlers(app)
    _register_health_check(app)

    return app


def _register_frontend(app: Flask) -> None:
    """Serve the dashboard (web/frontend) from the same origin as the API.

    Without these routes http://localhost:5000/ answers 404: the API blueprint
    only lives under /api and nothing served index.html.
    """
    @app.route('/', methods=['GET'])
    def index():
        return send_from_directory(FRONTEND_DIR, 'index.html')

    @app.route('/css/<path:filename>', methods=['GET'])
    def frontend_css(filename):
        return send_from_directory(FRONTEND_DIR / 'css', filename)

    @app.route('/js/<path:filename>', methods=['GET'])
    def frontend_js(filename):
        return send_from_directory(FRONTEND_DIR / 'js', filename)


def _configure_queries(app: Flask) -> None:
    """Monkey-patch the queries module so every helper uses the configured db_path.

    This keeps route handlers simple (they call queries.foo() with no args)
    while still letting tests override the database path per-app.
    """
    import queries as q

    configured_path = app.config['DATABASE_PATH']
    helpers = [
        'get_all_machines', 'get_machine_by_code', 'get_all_simulations',
        'get_simulation_summary', 'get_hourly_totals', 'get_machine_measurements',
        'get_export_data', 'validate_simulation_id', 'validate_machine_code',
        'insert_import', 'bulk_insert_real_measurements', 'list_imports',
        'get_import_detail', 'delete_import', 'get_real_measurements',
        'get_comparison',
        'get_or_create_live_import', 'upsert_real_measurements',
        'refresh_live_import_bounds',
    ]
    for name in helpers:
        original = getattr(q, name)

        def make_wrapper(fn):
            def wrapper(*args, **kwargs):
                kwargs.setdefault('db_path', configured_path)
                return fn(*args, **kwargs)
            wrapper.__name__ = fn.__name__
            wrapper.__doc__ = fn.__doc__
            return wrapper

        setattr(q, name, make_wrapper(original))


def _register_health_check(app: Flask) -> None:
    @app.route('/api/health', methods=['GET'])
    @app.route('/health', methods=['GET'])
    def health():
        db_path = app.config.get('DATABASE_PATH')
        db_ok = Path(db_path).exists() if db_path else False
        return jsonify({
            'status': 'ok' if db_ok else 'degraded',
            'database': 'connected' if db_ok else 'missing'
        })


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({'error': 'Bad request'}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Resource not found'}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({'error': 'Method not allowed'}), 405

    @app.errorhandler(500)
    def internal_error(e):
        # Do NOT expose the exception details — they may leak internals.
        app.logger.exception('Unhandled exception')
        return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    app = create_app()
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('PORT', '5000'))
    debug = os.getenv('FLASK_DEBUG', '0') == '1'
    app.run(host=host, port=port, debug=debug)
