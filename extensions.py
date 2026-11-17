"""
extensions.py — Instantiate Flask extensions here to avoid circular imports.
Import `db` from this module everywhere (models, app, etc.).
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
