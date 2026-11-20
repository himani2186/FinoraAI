"""
app.py — Finora AI Flask application (app-factory pattern).
"""

import os
import re
import json
import functools
from datetime import datetime, date
from decimal import Decimal

import jinja2
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, jsonify, flash, abort,
)
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

from extensions import db
from config import config
from models import User, Transaction, Budget, Category, seed_categories
from sms_parser import parse_sms
from ai_service import get_financial_advice, build_user_context
from utils import (
    get_month_stats,
    get_category_breakdown,
    seed_sample_data,
)


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app(config_name: str | None = None) -> Flask:
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    base_dir = os.path.abspath(os.path.dirname(__file__))
    templates_dir = os.path.join(base_dir, 'templates')
    static_dir = os.path.join(base_dir, 'static')

    app = Flask(
        __name__,
        template_folder=templates_dir,
        static_folder=static_dir,
    )

    # Multi-path Jinja loader to handle nested repo structures on Render
    candidate_template_dirs = [
        templates_dir,
        os.path.join(os.getcwd(), 'templates'),
        os.path.join(base_dir, 'finora-ai', 'templates'),
        os.path.join(os.path.dirname(base_dir), 'templates'),
    ]
    valid_loaders = [
        jinja2.FileSystemLoader(p)
        for p in candidate_template_dirs
        if os.path.isdir(p)
    ]
    if valid_loaders:
        app.jinja_loader = jinja2.ChoiceLoader(valid_loaders)

    if not os.path.exists(os.path.join(templates_dir, 'index.html')):
        print(
            f"[Finora Startup Warning] 'templates/index.html' not found in {templates_dir}! "
            f"Directory listing of {base_dir}: {os.listdir(base_dir)}"
        )

    app.config.from_object(config.get(config_name, config['default']))

    # Ensure upload folder exists
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'static/uploads'), exist_ok=True)

    # Init extensions
    db.init_app(app)

    with app.app_context():
        try:
            db.create_all()
            # Ensure monthly_income column exists for existing databases
            try:
                from sqlalchemy import text
                db.session.execute(text("ALTER TABLE users ADD COLUMN monthly_income NUMERIC(12, 2) DEFAULT 0"))
                db.session.commit()
            except Exception:
                db.session.rollback()

            seed_categories()
            # Auto-seed demo account if empty
            if not User.query.filter_by(email='himani@example.com').first():
                demo = User(full_name='Himani', email='himani@example.com')
                demo.set_password('password123')
                db.session.add(demo)
                db.session.commit()
                seed_sample_data(demo.id)
        except Exception as db_err:
            app.logger.warning(f"Database initialization deferred or encountered: {db_err}")

    # Register routes
    _register_routes(app)

    return app


# ---------------------------------------------------------------------------
# Auth decorator
# ---------------------------------------------------------------------------

def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def _get_current_user() -> User | None:
    uid = session.get('user_id')
    if uid is None:
        return None
    return db.session.get(User, uid)


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------

def _register_routes(app: Flask) -> None:

    # -----------------------------------------------------------------------
    # Landing / Auth pages
    # -----------------------------------------------------------------------

    @app.route('/')
    def index():
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        return render_template('index.html')

    @app.route('/features')
    def features_page():
        return render_template('features.html')

    @app.route('/about')
    def about_page():
        return render_template('about.html')

    @app.route('/contact', methods=['GET', 'POST'])
    def contact_page():
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip()
            message = request.form.get('message', '').strip()
            if name and email and message:
                flash('Thank you for reaching out! The Finora AI team will contact you shortly.', 'success')
            else:
                flash('Please fill out all required fields before submitting.', 'danger')
            return redirect(url_for('contact_page'))
        return render_template('contact.html')

    @app.route('/api/contact', methods=['POST'])
    def api_contact():
        data = request.get_json(silent=True) or request.form
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        message = data.get('message', '').strip()
        if not (name and email and message):
            return jsonify({'success': False, 'error': 'Name, email, and message are required.'}), 400
        return jsonify({'success': True, 'message': 'Thank you! Your message has been received by Finora AI.'})

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if 'user_id' in session:
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')

            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                session.permanent = True
                session['user_id'] = user.id
                session['user_name'] = user.full_name
                flash('Welcome back, ' + user.full_name + '!', 'success')
                return redirect(url_for('dashboard'))
            flash('Invalid email or password.', 'danger')

        return render_template('login.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if 'user_id' in session:
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm = request.form.get('confirm_password', '')

            if not full_name or not email or not password:
                flash('All fields are required.', 'danger')
            elif password != confirm:
                flash('Passwords do not match.', 'danger')
            elif User.query.filter_by(email=email).first():
                flash('Email already registered.', 'danger')
            else:
                user = User(full_name=full_name, email=email)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                # Auto-seed sample data for new users
                try:
                    seed_sample_data(user.id)
                except Exception:
                    pass
                session['user_id'] = user.id
                session['user_name'] = user.full_name
                flash('Account created! Welcome to Finora AI.', 'success')
                return redirect(url_for('dashboard'))

        return render_template('register.html')

    @app.route('/logout')
    def logout():
        session.clear()
        flash('You have been logged out.', 'info')
        return redirect(url_for('index'))

    # -----------------------------------------------------------------------
    # Protected page views
    # -----------------------------------------------------------------------

    @app.route('/dashboard')
    @login_required
    def dashboard():
        user = _get_current_user()
        uid = session['user_id']
        now = datetime.utcnow()

        stats = get_month_stats(uid, now.month, now.year)
        if user and user.monthly_income and float(user.monthly_income) > 0:
            stats['income'] = float(user.monthly_income)
            stats['savings'] = round(stats['income'] - stats['expenses'], 2)
        category_breakdown = get_category_breakdown(uid, now.month, now.year)

        recent_txns = (
            Transaction.query
            .filter_by(user_id=uid)
            .order_by(Transaction.date.desc())
            .limit(5)
            .all()
        )

        budgets = Budget.query.filter_by(
            user_id=uid, month=now.month, year=now.year
        ).all()

        return render_template(
            'dashboard.html',
            user=user,
            stats=stats,
            category_breakdown=category_breakdown,
            recent_txns=recent_txns,
            budgets=budgets,
            current_month=now.strftime('%B %Y'),
        )

    @app.route('/sms-analyzer')
    @login_required
    def sms_analyzer():
        user = _get_current_user()
        return render_template('sms_analyzer.html', user=user)

    @app.route('/transactions')
    @login_required
    def transactions():
        user = _get_current_user()
        uid = session['user_id']
        categories = Category.query.order_by(Category.name).all()
        all_txns = (
            Transaction.query
            .filter_by(user_id=uid)
            .order_by(Transaction.date.desc())
            .all()
        )
        return render_template(
            'transactions.html',
            user=user,
            transactions=all_txns,
            categories=categories,
        )

    @app.route('/budgets')
    @login_required
    def budgets():
        user = _get_current_user()
        uid = session['user_id']
        now = datetime.utcnow()
        categories = Category.query.order_by(Category.name).all()
        current_budgets = Budget.query.filter_by(
            user_id=uid, month=now.month, year=now.year
        ).all()

        # Synchronize spent_amount from actual transactions for accuracy
        for b in current_budgets:
            spent = db.session.query(db.func.coalesce(db.func.sum(Transaction.amount), 0)).filter(
                Transaction.user_id == uid,
                Transaction.category == b.category,
                Transaction.type == 'expense',
                db.extract('month', Transaction.date) == now.month,
                db.extract('year', Transaction.date) == now.year,
            ).scalar()
            b.spent_amount = float(spent)
        db.session.commit()

        total_budget = sum(float(b.limit_amount) for b in current_budgets)
        total_spent  = sum(float(b.spent_amount or 0) for b in current_budgets)
        remaining    = max(0.0, total_budget - total_spent)
        pct_used     = round(total_spent / total_budget * 100) if total_budget > 0 else 0

        CATEGORY_ICONS = {
            'Food & Dining': '🍴', 'Food': '🍴', 'Shopping': '🛍️',
            'Transport': '🚗', 'Utilities': '💡', 'Bills & Utilities': '💡',
            'Entertainment': '🎬', 'Health': '💊', 'Education': '📚',
            'Travel': '✈️', 'Rent': '🏠', 'Other': '📂'
        }
        CATEGORY_COLORS = {
            'Food & Dining': '#06b6d4', 'Food': '#06b6d4', 'Shopping': '#a855f7',
            'Transport': '#eab308', 'Utilities': '#38bdf8', 'Bills & Utilities': '#38bdf8',
            'Entertainment': '#ec4899', 'Health': '#10b981', 'Other': '#8b5cf6'
        }

        budget_cards = []
        for b in current_budgets:
            pct = round(float(b.spent_amount or 0) / float(b.limit_amount) * 100) if b.limit_amount and float(b.limit_amount) > 0 else 0
            budget_cards.append({
                'id': b.id,
                'category': b.category,
                'icon': CATEGORY_ICONS.get(b.category, '📂'),
                'color': CATEGORY_COLORS.get(b.category, '#7c3aed'),
                'limit_amount': float(b.limit_amount),
                'spent_amount': float(b.spent_amount or 0),
                'remaining': max(0.0, float(b.limit_amount) - float(b.spent_amount or 0)),
                'pct': min(pct, 100),
                'raw_pct': pct,
            })

        # Weekly spending data for this month for the trend chart
        weekly_spending = [0, 0, 0, 0]
        txns = Transaction.query.filter(
            Transaction.user_id == uid,
            Transaction.type == 'expense',
            db.extract('month', Transaction.date) == now.month,
            db.extract('year', Transaction.date) == now.year,
        ).all()
        for t in txns:
            day = t.date.day if hasattr(t.date, 'day') else 1
            week_idx = min(3, (day - 1) // 7)
            weekly_spending[week_idx] += float(t.amount)
        weekly_spending = [round(w) for w in weekly_spending]
        if sum(weekly_spending) == 0 and total_spent > 0:
            weekly_spending = [round(total_spent * 0.25), round(total_spent * 0.3), round(total_spent * 0.2), round(total_spent * 0.25)]

        return render_template(
            'budgets.html',
            user=user,
            categories=categories,
            budgets=current_budgets,
            budget_cards=budget_cards,
            total_budget=total_budget,
            total_spent=total_spent,
            remaining=remaining,
            pct_used=pct_used,
            weekly_spending=weekly_spending,
            current_month=now.strftime('%B %Y'),
        )

    @app.route('/budget-alerts')
    @login_required
    def budget_alerts():
        user = _get_current_user()
        uid = session['user_id']
        now = datetime.utcnow()
        stats = get_month_stats(uid, now.month, now.year)
        budgets = Budget.query.filter_by(user_id=uid, month=now.month, year=now.year).all()

        total_budget = sum(float(b.limit_amount) for b in budgets)
        total_spent  = sum(float(b.spent_amount or 0) for b in budgets)
        remaining    = total_budget - total_spent
        pct_used     = round(total_spent / total_budget * 100) if total_budget > 0 else 0
        donut_offset = round(301.59 * (1 - pct_used / 100), 2)

        # Category bars sorted by pct descending
        CATEGORY_ICONS = {
            'Food & Dining': '🍔', 'Transport': '🚗', 'Shopping': '🛍️',
            'Entertainment': '🎬', 'Health': '💊', 'Utilities': '💡',
            'Education': '📚', 'Travel': '✈️', 'Rent': '🏠',
            'Salary': '💰', 'Freelance': '💻', 'Investment': '📈', 'Other': '📂',
        }
        cat_data = []
        for b in sorted(budgets, key=lambda x: float(x.spent_amount or 0) / float(x.limit_amount or 1), reverse=True):
            pct = round(float(b.spent_amount or 0) / float(b.limit_amount) * 100) if b.limit_amount else 0
            pct = min(pct, 100)
            cat_data.append({
                'category': b.category,
                'icon': CATEGORY_ICONS.get(b.category, '📂'),
                'spent': float(b.spent_amount or 0),
                'budget': float(b.limit_amount),
                'pct': pct,
                'color': '#ef4444' if pct >= 85 else ('#f59e0b' if pct >= 70 else '#7c3aed'),
            })

        # Highest-pct category for the critical alert card
        critical_alert = None
        if cat_data and cat_data[0]['pct'] >= 70:
            critical_alert = cat_data[0]

        # Speech bubble for mascot
        if critical_alert:
            speech = f"Watch out! You've used {critical_alert['pct']}% of your {critical_alert['category']} budget!"
        elif budgets:
            speech = "Great job keeping your spending in check this month!"
        else:
            speech = "Set up budgets to get smart alerts here!"

        return render_template(
            'budget_alerts.html', user=user,
            pct_used=pct_used, donut_offset=donut_offset,
            total_budget=total_budget, total_spent=total_spent,
            remaining=remaining, cat_data=cat_data,
            critical_alert=critical_alert, speech=speech,
            stats=stats,
        )

    @app.route('/spending-prediction')
    @login_required
    def spending_prediction():
        user = _get_current_user()
        uid = session['user_id']
        now = datetime.utcnow()

        stats = get_month_stats(uid, now.month, now.year)
        current_expenses = float(stats['expenses'])

        # Monthly income (set by user or fallback to transactions / default)
        user_income = float(user.monthly_income or 0) if user else 0
        income = user_income or float(stats['income'] or 0) or 30000.0

        # AI Spending Prediction based on both spending habits and updated income:
        if current_expenses > 0 and income > current_expenses:
            # Model: base actual spending + moderate discretionary elasticity from income
            predicted = round(current_expenses + 0.15 * (income - current_expenses))
        elif current_expenses >= income and income > 0:
            # When expenses exceed or match income, predict target reduction to 95% of income
            predicted = round(income * 0.95)
        elif current_expenses > 0:
            predicted = round(current_expenses * 1.05)
        else:
            # 50-30-20 rule if zero expenses recorded yet
            predicted = round(income * 0.55)

        spending_pct = max(1, min(100, round(predicted / income * 100))) if income > 0 else 50
        potential_savings = max(0, round(income - predicted))
        savings_pct = max(0, min(100, round(potential_savings / income * 100))) if income > 0 else 50

        # Trend vs current month's actual expenses
        if current_expenses > 0:
            trend_pct = round((predicted - current_expenses) / current_expenses * 100, 1)
        else:
            trend_pct = 0.0

        # Build smooth last 3 months + predicted next month for chart
        monthly = []
        for i in range(2, -1, -1):
            raw_m = now.month - i - 1
            m = raw_m % 12 + 1
            y = now.year - (1 if raw_m < 0 else 0)
            s = get_month_stats(uid, m, y)
            exp = float(s['expenses'])
            # If past months have 0 recorded transactions, estimate baseline from prediction
            if exp == 0 and i > 0:
                if i == 2:
                    exp = round(predicted * 0.90)
                elif i == 1:
                    exp = round(predicted * 0.95)
            elif exp == 0 and i == 0:
                exp = current_expenses
            monthly.append({'label': datetime(y, m, 1).strftime('%b'), 'expenses': exp})

        next_month_dt = datetime(now.year + (now.month // 12), now.month % 12 + 1, 1)
        chart_labels   = [m['label'] for m in monthly] + [next_month_dt.strftime('%b')]
        chart_expenses = [m['expenses'] for m in monthly] + [predicted]

        # Category breakdown: project each category for next month
        raw_cats = get_category_breakdown(uid, now.month, now.year)
        cat_breakdown = []
        CATEGORY_ICONS = {
            'Food & Dining': '🍔', 'Transport': '🚗', 'Shopping': '🛍️',
            'Entertainment': '🎬', 'Health': '💊', 'Utilities': '💡',
            'Education': '📚', 'Travel': '✈️', 'Rent': '🏠',
            'Salary': '💰', 'Freelance': '💻', 'Investment': '📈', 'Other': '📂',
        }

        if raw_cats and current_expenses > 0:
            scale_ratio = predicted / current_expenses
            for c in raw_cats:
                cat_amt = float(c['amount'])
                pred_amt = round(cat_amt * scale_ratio)
                diff_pct = round((pred_amt - cat_amt) / cat_amt * 100) if cat_amt > 0 else 0
                cat_breakdown.append({
                    'category': c['category'],
                    'icon': CATEGORY_ICONS.get(c['category'], '📂'),
                    'current': cat_amt,
                    'predicted': pred_amt,
                    'diff_pct': diff_pct,
                })
        else:
            # Fallback categories based on income allocation
            defaults = [
                ('Food & Dining', '🍔', 0.28),
                ('Shopping', '🛍️', 0.22),
                ('Transport', '🚗', 0.12),
                ('Utilities', '💡', 0.18),
            ]
            for cat_name, icon, ratio in defaults:
                amt = round(predicted * ratio)
                cat_breakdown.append({
                    'category': cat_name,
                    'icon': icon,
                    'current': round(amt * 0.95),
                    'predicted': amt,
                    'diff_pct': 5,
                })

        return render_template(
            'spending_prediction.html', user=user,
            income=income,
            chart_labels=chart_labels,
            chart_expenses=chart_expenses,
            predicted=predicted,
            trend_pct=trend_pct,
            spending_pct=spending_pct,
            savings_pct=savings_pct,
            cat_breakdown=cat_breakdown,
            potential_savings=potential_savings,
        )

    @app.route('/financial-health')
    @login_required
    def financial_health():
        user = _get_current_user()
        uid = session['user_id']
        now = datetime.utcnow()
        stats = get_month_stats(uid, now.month, now.year)

        income   = float(user.monthly_income or 0) or (stats['income'] if stats['income'] > 0 else 1)
        expenses = stats['expenses']
        savings  = income - expenses

        savings_rate = max(0, min(100, round(savings / income * 200))) if income > 0 else 0

        budgets_this_month = Budget.query.filter_by(user_id=uid, month=now.month, year=now.year).all()
        if budgets_this_month:
            over = sum(1 for b in budgets_this_month if float(b.spent_amount or 0) > float(b.limit_amount))
            discipline = max(0, round((1 - over / len(budgets_this_month)) * 100))
        else:
            discipline = 100

        expense_ctrl   = max(0, min(100, round((1 - expenses / income) * 100))) if income > 0 else 50
        goal_progress  = min(100, round(savings_rate * 1.1))
        overall        = round((savings_rate + discipline + expense_ctrl + goal_progress) / 4)

        if overall >= 80:   label, emoji = 'Excellent', '⭐'
        elif overall >= 60: label, emoji = 'Good',      '👍'
        elif overall >= 40: label, emoji = 'Fair',      '⚠️'
        else:               label, emoji = 'Needs Work','🔧'

        arc_offset = round(439.82 * (1 - overall / 100), 2)

        return render_template(
            'financial_health.html', user=user,
            overall=overall, arc_offset=arc_offset,
            label=label, emoji=emoji,
            savings_rate=savings_rate, discipline=discipline,
            expense_ctrl=expense_ctrl, goal_progress=goal_progress,
            stats=stats,
        )

    # -----------------------------------------------------------------------
    # API: set monthly income
    # -----------------------------------------------------------------------
    @app.route('/api/set-income', methods=['POST'])
    @login_required
    def api_set_income():
        data   = request.get_json(silent=True) or {}
        try:
            amount = float(data.get('income', 0))
            if amount < 0:
                return jsonify({'success': False, 'error': 'Income must be non-negative'}), 400
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'Invalid income value'}), 400
        user = _get_current_user()
        user.monthly_income = amount
        db.session.commit()
        return jsonify({'success': True, 'income': amount})

    @app.route('/reports')
    @login_required
    def reports():
        user = _get_current_user()
        uid = session['user_id']
        now = datetime.utcnow()

        # Build last 6 months of stats for the chart
        monthly_data = []
        for i in range(5, -1, -1):
            m = (now.month - i - 1) % 12 + 1
            y = now.year - ((now.month - i - 1) // 12 + (1 if (now.month - i - 1) < 0 else 0))
            s = get_month_stats(uid, m, y)
            monthly_data.append({
                'label': datetime(y, m, 1).strftime('%b %Y'),
                **s,
            })

        category_breakdown = get_category_breakdown(uid, now.month, now.year)

        return render_template(
            'reports.html',
            user=user,
            monthly_data=monthly_data,
            category_breakdown=category_breakdown,
        )

    @app.route('/ai-assistant')
    @login_required
    def ai_assistant():
        user = _get_current_user()
        return render_template('ai_assistant.html', user=user)

    @app.route('/profile')
    @login_required
    def profile():
        user = _get_current_user()
        return render_template('profile.html', user=user)

    # -----------------------------------------------------------------------
    # API — Dashboard stats (for Chart.js)
    # -----------------------------------------------------------------------

    @app.route('/api/dashboard-stats', methods=['GET'])
    @login_required
    def api_dashboard_stats():
        uid = session['user_id']
        now = datetime.utcnow()

        month = request.args.get('month', now.month, type=int)
        year  = request.args.get('year', now.year, type=int)

        stats = get_month_stats(uid, month, year)
        category_breakdown = get_category_breakdown(uid, month, year)

        # Last 6 months trend for income vs expenses chart
        monthly_trend = []
        for i in range(5, -1, -1):
            idx = (month - i - 1) % 12
            m = idx + 1
            y = year - ((month - i - 1) // 12 + (1 if (month - i - 1) < 0 else 0))
            s = get_month_stats(uid, m, y)
            monthly_trend.append({
                'label': datetime(y, m, 1).strftime('%b'),
                'income': s['income'],
                'expenses': s['expenses'],
                'savings': s['savings'],
            })

        # Recent 5 transactions
        recent = (
            Transaction.query
            .filter_by(user_id=uid)
            .order_by(Transaction.date.desc())
            .limit(5)
            .all()
        )

        return jsonify({
            'success': True,
            'data': {
                'stats': stats,
                'category_breakdown': category_breakdown,
                'monthly_trend': monthly_trend,
                'recent_transactions': [t.to_dict() for t in recent],
            }
        })

    # -----------------------------------------------------------------------
    # API — Transactions
    # -----------------------------------------------------------------------

    @app.route('/api/transactions', methods=['GET'])
    @login_required
    def api_get_transactions():
        uid = session['user_id']
        q = Transaction.query.filter_by(user_id=uid)

        t_type   = request.args.get('type')
        category = request.args.get('category')
        month    = request.args.get('month', type=int)
        year     = request.args.get('year', type=int)
        page     = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)

        if t_type:
            q = q.filter(Transaction.type == t_type)
        if category:
            q = q.filter(Transaction.category == category)
        if month:
            q = q.filter(db.extract('month', Transaction.date) == month)
        if year:
            q = q.filter(db.extract('year', Transaction.date) == year)

        q = q.order_by(Transaction.date.desc())
        paginated = q.paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'success': True,
            'data': {
                'transactions': [t.to_dict() for t in paginated.items],
                'total': paginated.total,
                'pages': paginated.pages,
                'page': paginated.page,
                'per_page': per_page,
            }
        })

    @app.route('/api/transactions', methods=['POST'])
    @login_required
    def api_create_transaction():
        uid = session['user_id']
        data = request.get_json(silent=True) or request.form

        try:
            amount   = Decimal(str(data.get('amount', 0)))
            txn_date = date.fromisoformat(data.get('date', date.today().isoformat()))
        except (ValueError, TypeError) as e:
            return jsonify({'success': False, 'error': f'Invalid data: {e}'}), 400

        txn = Transaction(
            user_id=uid,
            amount=amount,
            description=data.get('description', ''),
            merchant=data.get('merchant', ''),
            category=data.get('category', 'Other'),
            type=data.get('type', 'expense'),
            date=txn_date,
            source=data.get('source', 'manual'),
        )
        db.session.add(txn)
        db.session.commit()
        _update_budget_spent(uid, txn)
        return jsonify({'success': True, 'data': txn.to_dict()}), 201

    @app.route('/api/delete-transaction/<int:txn_id>', methods=['DELETE'])
    @login_required
    def api_delete_transaction(txn_id):
        uid = session['user_id']
        txn = Transaction.query.filter_by(id=txn_id, user_id=uid).first_or_404()
        db.session.delete(txn)
        db.session.commit()
        return jsonify({'success': True, 'data': {'message': 'Transaction deleted'}}), 200

    # -----------------------------------------------------------------------
    # API — Budgets
    # -----------------------------------------------------------------------

    @app.route('/api/budgets', methods=['GET'])
    @login_required
    def api_get_budgets():
        uid = session['user_id']
        now = datetime.utcnow()
        month = request.args.get('month', now.month, type=int)
        year  = request.args.get('year', now.year, type=int)

        budgets = Budget.query.filter_by(user_id=uid, month=month, year=year).all()
        return jsonify({'success': True, 'data': [b.to_dict() for b in budgets]})

    @app.route('/api/budgets', methods=['POST'])
    @login_required
    def api_create_budget():
        uid = session['user_id']
        data = request.get_json(silent=True) or request.form

        now = datetime.utcnow()
        try:
            limit = Decimal(str(data.get('limit_amount', 0)))
            month = int(data.get('month', now.month))
            year  = int(data.get('year', now.year))
        except (ValueError, TypeError) as e:
            return jsonify({'success': False, 'error': f'Invalid data: {e}'}), 400

        category = data.get('category', 'Other')
        existing = Budget.query.filter_by(
            user_id=uid, category=category, month=month, year=year
        ).first()

        # Calculate actual spent amount from transactions for this category, month, and year
        spent = db.session.query(db.func.coalesce(db.func.sum(Transaction.amount), 0)).filter(
            Transaction.user_id == uid,
            Transaction.category == category,
            Transaction.type == 'expense',
            db.extract('month', Transaction.date) == month,
            db.extract('year', Transaction.date) == year,
        ).scalar()

        if existing:
            existing.limit_amount = limit
            existing.spent_amount = float(spent)
            db.session.commit()
            return jsonify({'success': True, 'data': existing.to_dict()}), 200

        budget = Budget(
            user_id=uid,
            category=category,
            limit_amount=limit,
            spent_amount=float(spent),
            month=month,
            year=year,
        )
        db.session.add(budget)
        db.session.commit()
        return jsonify({'success': True, 'data': budget.to_dict()}), 201

    # -----------------------------------------------------------------------
    # API — SMS Analyzer
    # -----------------------------------------------------------------------

    @app.route('/api/analyze-sms', methods=['POST'])
    @login_required
    def api_analyze_sms():
        data = request.get_json(silent=True) or {}
        sms_text = data.get('sms', '').strip()
        if not sms_text:
            return jsonify({'success': False, 'error': 'No SMS text provided'}), 400

        result = parse_sms(sms_text)
        return jsonify({'success': True, 'data': result})

    # -----------------------------------------------------------------------
    # API — AI Chat
    # -----------------------------------------------------------------------

    @app.route('/api/ai-chat', methods=['POST'])
    @login_required
    def api_ai_chat():
        user_message = ''
        try:
            api_key = app.config.get('GEMINI_API_KEY', '') or os.getenv('GEMINI_API_KEY', '')

            data = request.get_json(silent=True) or {}
            user_message = data.get('message', '').strip()
            if not user_message:
                return jsonify({'success': False, 'error': 'No message provided'}), 400

            uid = session['user_id']

            # Build context from recent transactions + budgets
            now = datetime.utcnow()
            recent_txns = (
                Transaction.query
                .filter_by(user_id=uid)
                .order_by(Transaction.date.desc())
                .limit(20)
                .all()
            )
            budgets = Budget.query.filter_by(
                user_id=uid, month=now.month, year=now.year
            ).all()

            txn_dicts    = [t.to_dict() for t in recent_txns]
            budget_dicts = [b.to_dict() for b in budgets]
            context      = build_user_context(txn_dicts, budget_dicts)

            result = get_financial_advice(
                user_message,
                user_context=context,
                api_key=api_key,
                transactions=txn_dicts,
                budgets=budget_dicts,
            )
            if result['success']:
                return jsonify({'success': True, 'data': {'reply': result['reply']}})
            return jsonify({'success': False, 'error': result.get('error', 'AI error')}), 500
        except Exception as err:
            app.logger.warning(f"Error handling /api/ai-chat: {err}")
            from ai_service import _generate_dynamic_financial_response
            fallback = _generate_dynamic_financial_response(user_message or 'financial advice', [], [])
            return jsonify({'success': True, 'data': {'reply': fallback}})

    # -----------------------------------------------------------------------
    # API — Update Profile
    # -----------------------------------------------------------------------

    @app.route('/api/update-profile', methods=['POST'])
    @login_required
    def api_update_profile():
        uid  = session['user_id']
        user = db.session.get(User, uid)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        data      = request.form or request.get_json(silent=True) or {}
        full_name = data.get('full_name', '').strip()
        if full_name:
            user.full_name   = full_name
            session['user_name'] = full_name

        if 'monthly_income' in data:
            try:
                user.monthly_income = float(data['monthly_income'])
            except (ValueError, TypeError):
                pass

        # Handle photo upload
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename:
                ext = file.filename.rsplit('.', 1)[-1].lower()
                if ext in {'png', 'jpg', 'jpeg', 'gif', 'webp'}:
                    filename   = secure_filename(f'avatar_{uid}.{ext}')
                    upload_dir = app.config.get('UPLOAD_FOLDER', 'static/uploads')
                    os.makedirs(upload_dir, exist_ok=True)
                    file.save(os.path.join(upload_dir, filename))
                    user.photo = url_for('static', filename=f'uploads/{filename}')

        db.session.commit()
        return jsonify({'success': True, 'data': {'user': user.to_dict()}})

    # -----------------------------------------------------------------------
    # Error handlers
    # -----------------------------------------------------------------------

    @app.errorhandler(404)
    def page_not_found(e):
        try:
            return render_template('errors/404.html'), 404
        except Exception:
            return "<div style='color:#fff;background:#0f0a1e;font-family:sans-serif;padding:3rem;text-align:center;'><h1>404 — Page Not Found</h1><p>Finora AI could not locate the requested resource.</p><a href='/' style='color:#a855f7;'>Return to Home</a></div>", 404

    @app.errorhandler(500)
    def internal_error(e):
        try:
            db.session.rollback()
        except Exception:
            pass
        try:
            return render_template('errors/500.html'), 500
        except Exception:
            return "<div style='color:#fff;background:#0f0a1e;font-family:sans-serif;padding:3rem;text-align:center;'><h1>500 — Internal Server Error</h1><p>Finora AI encountered an unexpected condition.</p><a href='/' style='color:#a855f7;'>Return to Home</a></div>", 500

    # -----------------------------------------------------------------------
    # Template context processors
    # -----------------------------------------------------------------------

    @app.context_processor
    def inject_globals():
        return {
            'current_user': _get_current_user(),
            'now': datetime.utcnow(),
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _update_budget_spent(user_id: int, txn: Transaction) -> None:
    """Update the spent_amount on the matching budget row, if one exists."""
    if txn.type != 'expense':
        return
    budget = Budget.query.filter_by(
        user_id=user_id,
        category=txn.category,
        month=txn.date.month,
        year=txn.date.year,
    ).first()
    if budget:
        budget.spent_amount = float(budget.spent_amount) + float(txn.amount)
        db.session.commit()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
