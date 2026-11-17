"""
utils.py — Shared helper utilities for Finora AI.
"""

import functools
from datetime import datetime
from typing import Optional

from flask import session, redirect, url_for, request, jsonify

from extensions import db
from models import User, Transaction, Budget


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def login_required(f):
    """Decorator: redirect to /login if user is not in session."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def get_current_user() -> Optional[User]:
    """Return the User object for the logged-in session, or None."""
    uid = session.get('user_id')
    if uid is None:
        return None
    return db.session.get(User, uid)


# ---------------------------------------------------------------------------
# Stats helpers
# ---------------------------------------------------------------------------

def get_month_stats(user_id: int, month: int, year: int) -> dict:
    """
    Return aggregated financial stats for a given month.

    Returns
    -------
    dict  {income, expenses, savings, transaction_count}
    """
    txns = Transaction.query.filter(
        Transaction.user_id == user_id,
        db.extract('month', Transaction.date) == month,
        db.extract('year',  Transaction.date) == year,
    ).all()

    income   = sum(float(t.amount) for t in txns if t.type == 'income')
    expenses = sum(float(t.amount) for t in txns if t.type == 'expense')

    return {
        'income':            round(income, 2),
        'expenses':          round(expenses, 2),
        'savings':           round(income - expenses, 2),
        'transaction_count': len(txns),
    }


def get_category_breakdown(user_id: int, month: int, year: int) -> list[dict]:
    """
    Return expense breakdown by category for a given month.

    Returns
    -------
    list of {'category': str, 'amount': float, 'percentage': float}
    """
    txns = Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.type    == 'expense',
        db.extract('month', Transaction.date) == month,
        db.extract('year',  Transaction.date) == year,
    ).all()

    by_cat: dict[str, float] = {}
    for t in txns:
        cat = t.category or 'Other'
        by_cat[cat] = by_cat.get(cat, 0.0) + float(t.amount)

    total = sum(by_cat.values()) or 1.0
    return [
        {
            'category':   cat,
            'amount':     round(amt, 2),
            'percentage': round(amt / total * 100, 1),
        }
        for cat, amt in sorted(by_cat.items(), key=lambda x: x[1], reverse=True)
    ]


# ---------------------------------------------------------------------------
# Sample data seeder (demo / onboarding)
# ---------------------------------------------------------------------------

_SAMPLE_TRANSACTIONS = [
    {'amount': 25000,  'description': 'Monthly Salary',          'merchant': 'Employer',    'category': 'Salary',       'type': 'income',  'day': 1},
    {'amount': 500,    'description': 'Swiggy dinner',           'merchant': 'Swiggy',      'category': 'Food & Dining','type': 'expense', 'day': 2},
    {'amount': 1200,   'description': 'Amazon purchase',         'merchant': 'Amazon',      'category': 'Shopping',     'type': 'expense', 'day': 3},
    {'amount': 199,    'description': 'Uber ride',               'merchant': 'Uber',        'category': 'Transport',    'type': 'expense', 'day': 4},
    {'amount': 499,    'description': 'Netflix subscription',    'merchant': 'Netflix',     'category': 'Entertainment','type': 'expense', 'day': 5},
    {'amount': 350,    'description': 'Zomato lunch',            'merchant': 'Zomato',      'category': 'Food & Dining','type': 'expense', 'day': 7},
    {'amount': 2500,   'description': 'Electricity bill',        'merchant': 'BESCOM',      'category': 'Utilities',    'type': 'expense', 'day': 8},
    {'amount': 850,    'description': 'Pharmacy',                'merchant': 'Apollo',      'category': 'Health',       'type': 'expense', 'day': 10},
    {'amount': 3000,   'description': 'Freelance payment',       'merchant': 'Client',      'category': 'Freelance',    'type': 'income',  'day': 12},
    {'amount': 450,    'description': 'Rapido ride',             'merchant': 'Rapido',      'category': 'Transport',    'type': 'expense', 'day': 14},
    {'amount': 1799,   'description': 'Myntra clothing',         'merchant': 'Myntra',      'category': 'Shopping',     'type': 'expense', 'day': 16},
    {'amount': 299,    'description': 'Spotify Premium',         'merchant': 'Spotify',     'category': 'Entertainment','type': 'expense', 'day': 18},
    {'amount': 650,    'description': 'Dinner at restaurant',    'merchant': 'Mainland China','category':'Food & Dining','type': 'expense', 'day': 20},
    {'amount': 999,    'description': 'Jio recharge',            'merchant': 'Jio',         'category': 'Utilities',    'type': 'expense', 'day': 22},
    {'amount': 500,    'description': 'ATM withdrawal',          'merchant': 'ATM',         'category': 'Other',        'type': 'expense', 'day': 24},
]

_SAMPLE_BUDGETS = [
    {'category': 'Food & Dining', 'limit_amount': 5000},
    {'category': 'Shopping',      'limit_amount': 4000},
    {'category': 'Transport',     'limit_amount': 2000},
    {'category': 'Utilities',     'limit_amount': 3500},
    {'category': 'Entertainment', 'limit_amount': 1500},
]


def seed_sample_data(user_id: int) -> int:
    """
    Insert sample transactions and budgets for a new/demo user.
    Returns the number of transactions created.
    """
    from datetime import date as _date

    now   = datetime.utcnow()
    month = now.month
    year  = now.year
    count = 0

    for sample in _SAMPLE_TRANSACTIONS:
        txn_date = _date(year, month, min(sample['day'], 28))
        txn = Transaction(
            user_id=user_id,
            amount=sample['amount'],
            description=sample['description'],
            merchant=sample['merchant'],
            category=sample['category'],
            type=sample['type'],
            date=txn_date,
            source='sample',
        )
        db.session.add(txn)
        count += 1

    for s_budget in _SAMPLE_BUDGETS:
        # Calculate how much has already been "spent" via sample transactions
        spent = sum(
            float(t['amount']) for t in _SAMPLE_TRANSACTIONS
            if t['category'] == s_budget['category'] and t['type'] == 'expense'
        )
        budget = Budget(
            user_id=user_id,
            category=s_budget['category'],
            limit_amount=s_budget['limit_amount'],
            spent_amount=spent,
            month=month,
            year=year,
        )
        db.session.add(budget)

    db.session.commit()
    return count
