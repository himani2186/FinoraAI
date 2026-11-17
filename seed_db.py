"""
seed_db.py — Initialize database and seed demo user 'himani@example.com'
"""

from app import create_app
from extensions import db
from models import User, Category, Transaction, Budget, seed_categories
from utils import seed_sample_data

app = create_app()

with app.app_context():
    db.create_all()
    seed_categories()

    # Check if demo user already exists
    demo_user = User.query.filter_by(email='himani@example.com').first()
    if not demo_user:
        demo_user = User(
            full_name='Himani',
            email='himani@example.com',
            photo=None
        )
        demo_user.set_password('password123')
        db.session.add(demo_user)
        db.session.commit()
        print(f"Created demo user: {demo_user.email} (id={demo_user.id})")

        # Seed sample data for Himani
        count = seed_sample_data(demo_user.id)
        print(f"Seeded {count} sample transactions and budgets for Himani.")
    else:
        print("Demo user already exists.")

    print("Database initialization and seeding complete!")
