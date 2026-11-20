"""
test_app.py — Automated endpoint testing suite for Finora AI
"""
from app import create_app
from extensions import db
from models import User, Transaction, Budget

app = create_app('testing')
client = app.test_client()

def run_tests():
    print("Testing Finora AI routes and APIs...\n")

    # Ensure demo user exists in test DB
    from utils import seed_sample_data
    with app.app_context():
        user = User.query.filter_by(email='himani@example.com').first()
        if not user:
            user = User(full_name='Himani', email='himani@example.com')
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            seed_sample_data(user.id)

    # 1. Landing page
    res = client.get('/')
    assert res.status_code == 200, f"Landing failed: {res.status_code}"
    assert b"Take Control" in res.data, "Landing copy missing"
    assert b"features" in res.data and b"about" in res.data and b"contact" in res.data
    print(" [PASS] GET / (Landing Page with Features, About, Contact)")

    # 1b. Standalone Marketing Pages
    res_f = client.get('/features')
    assert res_f.status_code == 200
    assert b"All Capabilities" in res_f.data or b"Capabilities" in res_f.data
    print(" [PASS] GET /features")

    res_a = client.get('/about')
    assert res_a.status_code == 200
    assert b"Our Mission" in res_a.data
    print(" [PASS] GET /about")

    res_c = client.get('/contact')
    assert res_c.status_code == 200
    assert b"Contact" in res_c.data
    print(" [PASS] GET /contact")

    res_c_api = client.post('/api/contact', json={'name': 'Himani', 'email': 'himani@example.com', 'message': 'Great app!'})
    assert res_c_api.status_code == 200 and res_c_api.get_json()['success'] is True
    print(" [PASS] POST /api/contact")

    # 2. Login GET
    res = client.get('/login')
    assert res.status_code == 200
    assert b"Welcome Back!" in res.data
    print(" [PASS] GET /login")

    # 3. Register GET
    res = client.get('/register')
    assert res.status_code == 200
    assert b"Create Account" in res.data
    print(" [PASS] GET /register")

    # 4. Login POST
    res = client.post('/login', data={
        'email': 'himani@example.com',
        'password': 'password123'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Welcome back" in res.data or b"Dashboard" in res.data
    print(" [PASS] POST /login (Authenticated session)")

    # 5. Dashboard & Income API
    res_inc = client.post('/api/set-income', json={'income': 60000})
    assert res_inc.status_code == 200 and res_inc.get_json()['success'] is True
    print(" [PASS] POST /api/set-income -> Income updated to 60,000")

    res = client.get('/dashboard')
    assert res.status_code == 200
    assert b"Total Income" in res.data
    assert b"60,000" in res.data
    assert b"Expense Breakdown" in res.data
    print(" [PASS] GET /dashboard (with dynamic income 60,000)")

    # 6. SMS Analyzer
    res = client.get('/sms-analyzer')
    assert res.status_code == 200
    assert b"UPI &amp; SMS Analyzer" in res.data or b"UPI & SMS Analyzer" in res.data
    print(" [PASS] GET /sms-analyzer")

    # 7. SMS Parser API
    res = client.post('/api/analyze-sms', json={
        'sms': 'Rs. 500 debited from your account for UPI payment at Swiggy'
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert data['data']['amount'] == 500.0 or data['data']['amount'] == '500' or float(data['data']['amount']) == 500.0
    print(f" [PASS] POST /api/analyze-sms -> Extracted: {data['data']}")

    # 8. Transactions Page
    res = client.get('/transactions')
    assert res.status_code == 200
    assert b"All Transactions" in res.data
    print(" [PASS] GET /transactions")

    # 9. Budgets Page & API
    res_b = client.post('/api/budgets', json={'category': 'Food & Dining', 'limit_amount': 7500})
    assert res_b.status_code in [200, 201] and res_b.get_json()['success'] is True
    print(" [PASS] POST /api/budgets -> Set Food & Dining limit to 7,500")

    res = client.get('/budgets')
    assert res.status_code == 200
    assert b"Monthly Budget Planner" in res.data
    assert b"7,500" in res.data
    print(" [PASS] GET /budgets (with updated 7,500 budget limit)")

    # 10. AI Assistant Page
    res = client.get('/ai-assistant')
    assert res.status_code == 200
    assert b"Gemini AI Financial Assistant" in res.data
    print(" [PASS] GET /ai-assistant")

    # 11. Profile Page
    res = client.get('/profile')
    assert res.status_code == 200
    assert b"Profile Settings" in res.data
    print(" [PASS] GET /profile")

    # 12. Reports Page
    res = client.get('/reports')
    assert res.status_code == 200
    assert b"Financial Reports" in res.data
    print(" [PASS] GET /reports")

    # 13. Budget Alerts Page
    res = client.get('/budget-alerts')
    assert res.status_code == 200, f"Budget Alerts failed: {res.status_code}"
    assert b"Smart Budget Alerts" in res.data or b"Budget Alert" in res.data
    print(" [PASS] GET /budget-alerts")

    # 14. Spending Prediction Page
    res = client.get('/spending-prediction')
    assert res.status_code == 200, f"Spending Prediction failed: {res.status_code}"
    assert b"Spending Prediction" in res.data or b"Predicted" in res.data
    print(" [PASS] GET /spending-prediction")

    # 15. Financial Health Score Page
    res = client.get('/financial-health')
    assert res.status_code == 200, f"Financial Health failed: {res.status_code}"
    assert b"Financial Health" in res.data or b"Health Score" in res.data
    print(" [PASS] GET /financial-health")

    # 16. Logout GET -> Redirect to index
    res = client.get('/logout', follow_redirects=False)
    assert res.status_code == 302, f"Logout status should be 302, got {res.status_code}"
    assert res.headers['Location'] == '/' or res.headers['Location'].endswith('/'), f"Logout location wrong: {res.headers['Location']}"
    res_follow = client.get('/logout', follow_redirects=True)
    assert res_follow.status_code == 200
    assert b"Take Control" in res_follow.data, "Should redirect to landing/index page"
    print(" [PASS] GET /logout -> Redirects to Index page (/)")

    print("\nALL 16 TESTS PASSED! Finora AI is fully functioning.")

if __name__ == '__main__':
    run_tests()
