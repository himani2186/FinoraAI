"""
run.py — Development entry point.
Initialises the DB, auto-creates demo user if needed, and starts the Flask dev server.
"""
from app import create_app
from extensions import db
from models import User, seed_categories
from utils import seed_sample_data

app = create_app('development')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_categories()

        # Auto-create demo user for instant test if no users exist
        demo_user = User.query.filter_by(email='himani@example.com').first()
        if not demo_user:
            demo_user = User(
                full_name='Himani',
                email='himani@example.com'
            )
            demo_user.set_password('password123')
            db.session.add(demo_user)
            db.session.commit()
            seed_sample_data(demo_user.id)
            print("Demo user created: himani@example.com / password123")

    print("\n" + "="*50)
    print(" Finora AI Server Running at: http://localhost:5000")
    print(" Demo Account: himani@example.com / password123")
    print("="*50 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
