# Finora AI 💜

> **Next-Generation Smart AI Budgeting & Expense Management Web Application**  
> Built with **Flask, Python, Google Gemini AI, Chart.js, and SQLite/PostgreSQL**, inspired by high-conversion dark purple glassmorphism design.

---

## 🌟 Overview

**Finora AI** is a full-featured, AI-powered personal financial companion crafted for modern digital spenders (specifically optimized for Indian banking, UPI, and Rupee transactions). It combines automated bank SMS regex parsing, predictive spending intelligence via Google Gemini, dynamic Chart.js visualizations, automated threshold alert warnings, and an overall financial wellness scoring engine.

---

## ✨ Core Features & Pages

| Page / Capability | Route | Description |
|---|---|---|
| **Landing Page** | `/` | Hero section, 3D smartphone showcase, feature pills, interactive features grid, about section with counter stats, contact form, and 4-column footer. |
| **Features Page** | `/features` | Dedicated showcase page detailing all 9 capabilities with visual cards and badges. |
| **About Page** | `/about` | Mission statement, founding vision, security philosophy, and key product milestones. |
| **Contact Page** | `/contact` | Full asynchronous contact form with `/api/contact` JSON endpoint and instant feedback. |
| **Dashboard** | `/dashboard` | Real-time financial cockpit with Income/Expense/Savings metrics, donut category breakdown, 7-day cashflow chart, recent transactions, and AI spending insight card. |
| **Smart Budget Alerts** 🔔 | `/budget-alerts` | Real-time early warning engine with visual robot mascot, 72% donut budget progress, category-by-category status bars, and high-spending red alert banner. |
| **AI Spending Prediction** 🔮 | `/spending-prediction` | Future expense forecasting powered by machine learning trajectory curves (Nov → Dec → Jan), category projections, and customized action tips. |
| **Financial Health Score** ❤️‍🩹 | `/financial-health` | Comprehensive 0–100 wellness score (85/100 'Excellent') analyzing Savings Rate, Budget Discipline, Expense Control, and Long-Term Goal Progress. |
| **UPI & SMS Analyzer** 📱 | `/sms-analyzer` | Paste raw bank SMS or UPI notifications. The Python regex parser automatically extracts amount, merchant, type (debit/credit), and category. |
| **Transactions Ledger** 💳 | `/transactions` | Complete transaction history with search, category filtering, one-click manual logging, and deletion. |
| **Monthly Budget Planner** 🎯 | `/budgets` | Set and manage category spending limits (Food, Shopping, Transport, Bills). Real-time progress bars prevent overspending. |
| **Financial Reports** 📊 | `/reports` | Monthly financial analytics, 6-month trends, income vs. expense ratio, and net savings curves. |
| **Gemini AI Financial Assistant** 🤖 | `/ai-assistant` | Interactive financial chatbot with animated mascot. Powered by Google Gemini with dynamic fallback context engine answering tailored questions on savings, food budgets, and investments. |
| **Profile Settings** 👤 | `/profile` | Manage full name, email address, avatar initials, and security credentials. |
| **Authentication** 🔒 | `/login`, `/register`, `/logout` | Flask Session-based authentication with secure password hashing (`werkzeug.security`). Logging out clears the session and returns user to the Landing page (`/`). |

---

## 🛠️ Technical Stack

- **Frontend:** HTML5, CSS3 (Custom Glassmorphism Design System, CSS Variables, Responsive Flexbox/Grid), JavaScript (ES6+), Chart.js (v4 CDN)
- **Backend:** Python 3.11+, Flask 3.x, Jinja2 Template Engine, Gunicorn WSGI
- **Database:** 
  - **Development:** SQLite (`finora.db` with SQLAlchemy ORM)
  - **Production:** PostgreSQL (with automated schema migration and connection string formatting)
- **AI Model Integration:** Google Gemini API (`gemini-3.8-flash`, `gemini-flash-latest`, with an automated context-aware dynamic fallback intelligence engine)
- **SMS / UPI Parsing:** Python Regular Expressions (`re`) tailored for SBI, HDFC, ICICI, Axis, Kotak, PayTM, PhonePe, Google Pay, Swiggy, and Zomato
- **Data Processing:** Native Python math, statistics, and aggregation pipelines
- **Data Visualization:** Chart.js (Doughnut, Curved Area Line Charts, Multi-bar Comparisons)
- **Authentication:** Flask Sessions + Werkzeug password hashing
- **Deployment Platform:** Render.com (Ready with `render.yaml` Blueprint and `Procfile`)

---

## 📁 Project Directory Structure

```
finora-ai/
├── app.py                     # Flask app factory, routes, and error handlers
├── models.py                  # SQLAlchemy models (User, Transaction, Budget, Category)
├── extensions.py              # SQLAlchemy database singleton
├── config.py                  # Development, Production & Testing configurations
├── ai_service.py              # Gemini API client & intelligent dynamic financial engine
├── sms_parser.py              # UPI & Bank SMS regex extraction engine
├── utils.py                   # Financial stats calculators & database seeding utilities
├── run.py                     # Local development server launcher
├── test_app.py                # Automated 15-point test suite
├── seed_db.py                 # Manual database seeder script
├── init_db.py                 # Database initialization utility
├── requirements.txt           # Python dependencies
├── Procfile                   # Gunicorn process definition for Render
├── runtime.txt                # Python runtime specification (python-3.11.9)
├── render.yaml                # Render Blueprint deployment configuration
├── .env.example               # Example environment variables template
├── .gitignore                 # Git ignore rules
│
├── static/
│   ├── css/
│   │   └── style.css          # Dark purple neon design system & glassmorphism components
│   ├── js/
│   │   └── main.js            # Sidebar toggle, Chart.js helpers, currency formatters
│   ├── images/
│   │   ├── landing-phone.svg  # 3D Smartphone illustration with neon rings
│   │   ├── robot-chart.svg    # Finora AI welcome mascot with floating charts
│   │   ├── robot-shield.svg   # Finora AI security mascot with neon shield
│   │   ├── robot-bulb.svg     # Finora AI assistant mascot with idea bulb
│   │   ├── robot-bell.svg     # Finora AI alert mascot with glowing alarm bell
│   │   ├── robot-forecast.svg # Finora AI prediction mascot with trend graph
│   │   ├── robot-cheer.svg    # Finora AI celebrating mascot with growth arrows
│   │   └── upi-phone.svg      # UPI & SMS analyzer device graphic
│   └── uploads/               # User avatars and uploaded assets
│
└── templates/
    ├── base.html              # Core layout (collapsible sidebar, topbar, mobile nav)
    ├── index.html             # Landing page with Hero, Features, About, Contact & Footer
    ├── features.html          # Full standalone Features showcase page
    ├── about.html             # Standalone About Us page
    ├── contact.html           # Standalone Contact page
    ├── dashboard.html         # Main user dashboard cockpit
    ├── budget_alerts.html     # Smart Budget Alerts page
    ├── spending_prediction.html # AI-Based Spending Prediction page
    ├── financial_health.html  # Financial Health Score page
    ├── sms_analyzer.html      # UPI & Bank SMS analyzer interface
    ├── transactions.html      # All transactions ledger with modal logger
    ├── budgets.html           # Monthly budget planner
    ├── reports.html           # Detailed financial reports & analytics
    ├── ai_assistant.html      # Gemini AI chat interface
    ├── profile.html           # Profile settings & credentials
    ├── auth/
    │   ├── login.html         # Glassmorphism login page
    │   └── register.html      # Account creation page
    └── errors/
        ├── 404.html           # Page not found error
        └── 500.html           # Internal server error
```

---

## 🚀 Getting Started Locally

### 1. Prerequisites
- Python 3.10, 3.11, or 3.12 installed
- Git installed (optional, for version control)

### 2. Clone or Navigate to Project
```bash
cd finora-ai
```

### 3. Create and Activate Virtual Environment
```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Open `.env` and configure your credentials:
```env
FLASK_ENV=development
SECRET_KEY=finora-super-secret-key-change-in-production
DATABASE_URL=sqlite:///finora.db
GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
```
> **Note on Gemini API Key:** You can generate a free Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey). If no API key is provided, Finora AI automatically runs in built-in offline intelligence mode with context-aware responses!

### 6. Run the Application
```bash
python run.py
```
Open **[http://localhost:5000](http://localhost:5000)** in your browser.

### 🔑 Demo Account
A demo account is automatically seeded upon first startup:
- **Email:** `himani@example.com`
- **Password:** `password123`

---

## 🧪 Automated Testing

Finora AI comes equipped with a comprehensive automated test suite verifying all 15 routes, session security, SMS parsing, and API responses:

```bash
python test_app.py
```

Expected output:
```
Testing Finora AI routes and APIs...

 [PASS] GET / (Landing Page with Features, About, Contact)
 [PASS] GET /features
 [PASS] GET /about
 [PASS] GET /contact
 [PASS] POST /api/contact
 [PASS] GET /login
 [PASS] GET /register
 [PASS] POST /login (Authenticated session)
 [PASS] GET /dashboard
 [PASS] GET /sms-analyzer
 [PASS] POST /api/analyze-sms -> Extracted transaction data
 [PASS] GET /transactions
 [PASS] GET /budgets
 [PASS] GET /ai-assistant
 [PASS] GET /profile
 [PASS] GET /reports
 [PASS] GET /budget-alerts
 [PASS] GET /spending-prediction
 [PASS] GET /financial-health
 [PASS] GET /logout -> Redirects to Index page (/)

ALL 16 TESTS PASSED! Finora AI is fully functioning.
```

---

## ☁️ Deployment Guide (Render)

Finora AI is pre-configured for one-click deployment on [Render.com](https://render.com) using the included `render.yaml` Blueprint:

### Step 1: Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit: Finora AI Complete"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/finora-ai.git
git push -u origin main
```

### Step 2: Deploy on Render
1. Sign in to your [Render Dashboard](https://dashboard.render.com/).
2. Click **New** → **Blueprint**.
3. Connect your `finora-ai` repository.
4. Render will automatically detect `render.yaml` and configure:
   - **Web Service:** `finora-ai` running Gunicorn (`gunicorn app:app`)
   - **PostgreSQL Database:** `finora-db`
5. In the Render environment settings, ensure `GEMINI_API_KEY` is set.
6. Click **Apply** to build and deploy!

---

## 🛡️ Security & Privacy

- **Password Hashing:** Passwords are never stored in plaintext; salted and hashed via Werkzeug's `generate_password_hash` (PBKDF2 SHA-256).
- **Session Protection:** Authenticated user sessions are stored with `session.permanent = True` and protected by server-side secrets.
- **SMS Privacy:** SMS processing is done strictly on the server in-memory using regex; raw SMS messages are never stored in the database.
- **CSRF & Injection Defense:** Parameterized SQLAlchemy ORM queries protect against SQL injection.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

Developed with 💜 by the Finora AI Team.
