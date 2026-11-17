import os
import re
import socket
from dotenv import load_dotenv

load_dotenv()


def resolve_database_uri(raw_url: str) -> str:
    """
    Safely resolves the database URI for Render / production environments.
    1. Normalizes 'postgres://' to 'postgresql://' (required by SQLAlchemy 2.0).
    2. Validates that the database host is resolvable via DNS. If the host
       cannot be reached (e.g. cross-region Render internal hostname or deleted DB),
       it logs a warning and falls back to SQLite so Gunicorn never crashes with exit status 1.
    """
    if not raw_url:
        return 'sqlite:///finora_prod.db'

    if raw_url.startswith('postgres://'):
        raw_url = raw_url.replace('postgres://', 'postgresql://', 1)

    # Check DNS resolution for remote databases
    match = re.search(r'@([^:/]+)', raw_url)
    if match:
        host = match.group(1)
        try:
            socket.gethostbyname(host)
        except (socket.gaierror, socket.herror, OSError) as err:
            print(
                f"[Finora DB Warning] Host '{host}' cannot be resolved ({err}). "
                "Render internal hostnames require services in the same region, or an External Database URL. "
                "Gracefully falling back to SQLite ('finora_prod.db') to keep the server live!"
            )
            return 'sqlite:///finora_prod.db'

    return raw_url


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file upload
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


class DevelopmentConfig(Config):
    """Development configuration — uses SQLite."""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(os.path.dirname(__file__), 'finora.db')
    )
    SQLALCHEMY_ECHO = False  # Set True to log SQL queries


class TestingConfig(Config):
    """Testing configuration — in-memory SQLite."""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production configuration — PostgreSQL via DATABASE_URL env var with safe fallback."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True

    _raw_url = os.environ.get('DATABASE_URL', '')
    SQLALCHEMY_DATABASE_URI = resolve_database_uri(_raw_url)


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
