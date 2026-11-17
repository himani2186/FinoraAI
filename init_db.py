"""
init_db.py — One-shot script to initialise the database and seed default data.
Run once before first launch: python init_db.py
"""
from app import create_app
from extensions import db
from models import seed_categories

app = create_app('development')

with app.app_context():
    db.create_all()
    seed_categories()
    print("✅ Database initialised and categories seeded.")
