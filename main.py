import sys
import os
from flask import Flask
from dotenv import load_dotenv

from src.config.factory import create_app

def load_environment():
    """Load the appropriate .env file based on FLASK_ENV."""
    env = os.getenv('FLASK_ENV', 'development')
    env_file = f'.env.{env}'

    # Only load .env file if it exists (for local development)
    if os.path.exists(env_file):
        load_dotenv(env_file)
        print(f"✅ Loaded environment: {env} from {env_file}")
    else:
        # In production, env vars are already set - no file needed
        print(f"✅ Running in {env} mode - using system environment variables")

    return env


def ensure_config_ready():
    """Ensure config.py runs and config.pyi is generated before imports."""
    try:
        from src.config.config import config_sections
        print("✅ Config system initialized")
        return bool(config_sections)
    except Exception as e:
        print(f"❌ Error initializing config: {e}")
        return False


def create_application():
    """Create and return Flask application."""

    print("=== Initializing Sentinel Configuration System ===")

    # Step 0: Load environment variables FIRST
    current_env = load_environment()
    print(f"📦 Environment: {current_env}")
    print(f"📦 App Version: {os.getenv('APP_VERSION', 'unknown')}")

    configs = None

    # Step 1: Generate stub file first
    if not ensure_config_ready():
        print("Failed to initialize config system. Exiting.")
        sys.exit(1)

    # Step 2: Now safely import config sections
    try:
        from src.config.config import (
            application,
            security,
            server,
            database,
            integrations,
            logging
        )

        configs = {
            "application": application,
            "security": security,
            "server": server,
            "database": database,
            "integrations": integrations,
            "logging": logging,
        }

        print("✅ Loaded configs:", list(configs.keys()))

    except ImportError as e:
        print(f"❌ Failed to import configs: {e}")
        sys.exit(1)

    print("\n=== Starting Sentinel Application ===")

    # Custom error handling
    error_handlers = []

    # Blueprints
    blueprints = []

    try:
        # Create Flask app by passing config sections as parameters
        flask_app = create_app(
            Flask(__name__),
            configs=configs,
            blueprints=blueprints,
            error_handlers=error_handlers
        )

        print("✅ Sentinel application created successfully")
        return flask_app

    except AttributeError as e:
        print(f"❌ Configuration error: {e}")
        print("Make sure your config.yaml file has all required sections.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Application error: {e}")
        sys.exit(1)


# Create the app instance
app = create_application()

# For direct execution with Flask development server
if __name__ == '__main__':
    from src.config.config import server

    port = int(os.getenv('PORT', server.port))

    print(f"🚀 Starting Sentinel development server")
    print(f"   Host: {server.ip}")
    print(f"   Port: {port}")
    print(f"   Debug: {server.debug}")

    app.run(host=server.ip, port=port, debug=server.debug)