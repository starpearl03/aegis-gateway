import os
import logging as python_logging
from datetime import timedelta

from flask import send_from_directory
from flask_session import Session
from flask_bcrypt import Bcrypt

from src.modules.authentication.internal.admin_initializer import AdminInitializer
from src.shared.configs.exceptions.handlers.global_error_handler import register_global_error_handlers
from src.shared.data.database import db


def create_app(flask_app,
               configs, blueprints=None,
               error_handlers=None):
    """Create and configure the Flask application using passed config parameters."""

    if blueprints is None:
        blueprints = []
    if error_handlers is None:
        error_handlers = []

    # Initialize Flask app
    app = flask_app

    # Configure template directories - Flask will search in order
    current_dir = os.path.dirname(os.path.abspath(__file__))
    shared_templates_path = os.path.join(current_dir, '..', 'shared', 'ui', 'templates')
    shared_templates_path = os.path.abspath(shared_templates_path)

    app.template_folder = shared_templates_path

    # Validate required database config
    if not configs.get("database").uri:
        raise ValueError("Database URI is not set in the configuration.")

    # ============================================
    # Application Metadata
    # ============================================
    app.config['APP_NAME'] = configs.get("application").name
    app.config['APP_DESCRIPTION'] = configs.get("application").description
    app.config['APP_VERSION'] = configs.get("application").version

    # ============================================
    # Server Configuration
    # ============================================
    app.config['DEBUG'] = configs.get("server").debug

    # ============================================
    # Database Configuration
    # ============================================
    app.config['SQLALCHEMY_DATABASE_URI'] = configs.get("database").uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = configs.get("database").track_modifications
    app.config['SQLALCHEMY_ECHO'] = configs.get("database").echo

    # PostgresSQL Engine Options
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': configs.get("database").pool_size,
        'max_overflow': configs.get("database").max_overflow,
        'pool_timeout': configs.get("database").pool_timeout,
        'pool_recycle': configs.get("database").pool_recycle,
        'pool_pre_ping': configs.get("database").pool_pre_ping,
        'connect_args': {
            'connect_timeout': 10,
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5,
        }
    }

    # ============================================
    # Logging Configuration
    # ============================================
    logging_config = configs.get("logging")

    # Configure Python logging
    log_level = getattr(python_logging, logging_config.level.upper(), python_logging.INFO)

    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(logging_config.file_path)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Configure logging
    python_logging.basicConfig(
        level=log_level,
        format=logging_config.format,
        handlers=[
            python_logging.FileHandler(logging_config.file_path),
            python_logging.StreamHandler()  # Also log to console
        ]
    )

    # Set Flask's logger to use the same configuration
    app.logger.setLevel(log_level)

    # ============================================
    # Session Configuration
    # ============================================
    session_config = configs.get("security").session

    app.config['SECRET_KEY'] = session_config.secret_key
    app.config['SESSION_TYPE'] = session_config.type
    app.config['SESSION_SQLALCHEMY'] = db
    app.config['SESSION_SQLALCHEMY_TABLE'] = session_config.table_name
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=session_config.permanent_session_lifetime)

    # Session cookie settings
    app.config['SESSION_COOKIE_NAME'] = session_config.cookie_name
    app.config['SESSION_COOKIE_HTTPONLY'] = session_config.cookie_httponly
    app.config['SESSION_COOKIE_SECURE'] = session_config.cookie_secure
    app.config['SESSION_COOKIE_SAMESITE'] = session_config.cookie_samesite

    # Refresh session on each request
    app.config['SESSION_REFRESH_EACH_REQUEST'] = session_config.refresh_each_request

    # thread executor settings
    app.config['EXECUTOR_MAX_WORKERS'] = 10

    # ============================================
    # Initialize SQLAlchemy
    # ============================================
    db.init_app(app)

    # Create all tables (including sessions table) WITHIN app context
    with app.app_context():
        # Enable pgvector extension FIRST (before creating tables)
        try:
            app.logger.info("Enabling pgvector extension...")
            db.session.execute(db.text('CREATE EXTENSION IF NOT EXISTS vector;'))
            db.session.commit()
            app.logger.info("✅ pgvector extension enabled")
        except Exception as e:
            app.logger.warning(f"⚠️ Could not enable pgvector extension: {e}")
            db.session.rollback()

        # Now create all tables
        db.create_all()
        app.logger.info("Database tables created successfully")

        AdminInitializer.initialize()

        # Initialize Session AFTER tables are created and WITHIN app context
        Session(app)
        app.logger.info("Flask-Session initialized successfully")

    # ============================================
    # Password Hashing Configuration
    # ============================================
    password_config = configs.get("security").password
    app.config['BCRYPT_LOG_ROUNDS'] = password_config.bcrypt_rounds

    # Initialize Bcrypt
    bcrypt = Bcrypt(app)

    # ============================================
    # Integrations Configuration
    # ============================================
    integrations_config = configs.get("integrations")

    # Store integrations in app config for easy access
    app.config['INTEGRATIONS'] = {
        'AI': integrations_config.ai,
        'EMAIL': integrations_config.email,
        'TWILIO': integrations_config.twilio,
    }

    # ============================================
    # Register Blueprints (controllers)
    # ============================================
    for blueprint in blueprints:
        app.register_blueprint(blueprint)
        app.logger.info(f"Registered blueprint: {blueprint.name}")

    # ============================================
    # Register custom error handling
    # ============================================
    for error, handler in error_handlers:
        app.register_error_handler(error, handler)

    # ============================================
    # File Upload Configuration
    # ============================================
    uploads_config = configs.get("uploads")

    app.config['UPLOAD_FOLDER_ROOT'] = uploads_config.root_folder
    app.config['UPLOAD_FOLDER_CRIMINALS'] = uploads_config.criminals_folder
    app.config['UPLOAD_FOLDER_MISSING_PERSONS'] = uploads_config.missing_persons_folder
    app.config['UPLOAD_FOLDER_EVIDENCE'] = uploads_config.evidence_folder
    app.config['MAX_FILE_SIZE'] = uploads_config.max_file_size_mb * 1024 * 1024  # Convert to bytes
    app.config['ALLOWED_IMAGE_EXTENSIONS'] = set(uploads_config.allowed_image_extensions)
    app.config['ALLOWED_EVIDENCE_EXTENSIONS'] = set(uploads_config.allowed_evidence_extensions)

    # Create upload directories
    os.makedirs(uploads_config.criminals_folder, exist_ok=True)
    os.makedirs(uploads_config.missing_persons_folder, exist_ok=True)
    os.makedirs(uploads_config.evidence_folder, exist_ok=True)

    # Make upload folders accessible as static files for templates
    app.add_url_rule(
        f'/{uploads_config.root_folder}/<path:filename>',
        endpoint='uploads',
        view_func=lambda filename: send_from_directory(uploads_config.root_folder, filename)
    )

    @app.template_filter('image_url')
    def image_url_filter(image_path):
        """Convert database image path to URL-friendly format"""
        if not image_path:
            return ''

        # Remove 'uploads/' or 'uploads\' prefix
        path = image_path.replace('uploads/', '').replace('uploads\\', '')

        # Convert all backslashes to forward slashes
        path = path.replace('\\', '/')

        return path

    # ============================================
    # Register global error handlers
    # ============================================
    register_global_error_handlers(app)

    # ============================================
    # Initialize Executor (for background tasks) #Todo: create jobs to about the crimes in realtime for crime analysis
    # ============================================
    # executor = Executor(app)
    # app.executor = executor
    # app.logger.info("Flask-Executor initialized successfully")

    app.logger.info(f">> {app.config['APP_NAME']} v{app.config['APP_VERSION']} initialized successfully")

    return app