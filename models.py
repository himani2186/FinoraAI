from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    photo = db.Column(db.String(512), nullable=True, default=None)
    currency = db.Column(db.String(10), default='INR')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    transactions = db.relationship('Transaction', backref='user', lazy='dynamic',
                                   cascade='all, delete-orphan')
    budgets = db.relationship('Budget', backref='user', lazy='dynamic',
                              cascade='all, delete-orphan')

    # ------------------------------------------------------------------
    # Auth helpers
    # ------------------------------------------------------------------
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    # Flask-Login interface (without the mixin — we use plain sessions)
    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_active(self) -> bool:
        return True

    def get_id(self) -> str:
        return str(self.id)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'full_name': self.full_name,
            'email': self.email,
            'photo': self.photo,
            'currency': self.currency,
            'created_at': self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f'<User {self.email}>'


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------
class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    icon = db.Column(db.String(10), default='📂')
    color = db.Column(db.String(20), default='#7c3aed')

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'icon': self.icon,
            'color': self.color,
        }

    def __repr__(self) -> str:
        return f'<Category {self.name}>'


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------
class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'),
                        nullable=False, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    merchant = db.Column(db.String(255), nullable=True)
    category = db.Column(db.String(80), nullable=True)
    type = db.Column(db.String(10), nullable=False)          # 'income' | 'expense'
    date = db.Column(db.Date, default=datetime.utcnow().date, nullable=False)
    source = db.Column(db.String(50), default='manual')      # 'manual' | 'sms'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'amount': float(self.amount),
            'description': self.description,
            'merchant': self.merchant,
            'category': self.category,
            'type': self.type,
            'date': self.date.isoformat() if self.date else None,
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f'<Transaction {self.type} ₹{self.amount} on {self.date}>'


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------
class Budget(db.Model):
    __tablename__ = 'budgets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'),
                        nullable=False, index=True)
    category = db.Column(db.String(80), nullable=False)
    limit_amount = db.Column(db.Numeric(12, 2), nullable=False)
    spent_amount = db.Column(db.Numeric(12, 2), default=0.0)
    month = db.Column(db.Integer, nullable=False)   # 1–12
    year = db.Column(db.Integer, nullable=False)

    @property
    def percentage_used(self) -> float:
        if not self.limit_amount or float(self.limit_amount) == 0:
            return 0.0
        return round(float(self.spent_amount) / float(self.limit_amount) * 100, 2)

    @property
    def remaining(self) -> float:
        return max(0.0, float(self.limit_amount) - float(self.spent_amount))

    @property
    def is_over_budget(self) -> bool:
        return float(self.spent_amount) > float(self.limit_amount)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'category': self.category,
            'limit_amount': float(self.limit_amount),
            'spent_amount': float(self.spent_amount),
            'month': self.month,
            'year': self.year,
            'percentage_used': self.percentage_used,
            'remaining': self.remaining,
            'is_over_budget': self.is_over_budget,
        }

    def __repr__(self) -> str:
        return f'<Budget {self.category} {self.month}/{self.year}>'


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------
DEFAULT_CATEGORIES = [
    {'name': 'Food & Dining',   'icon': '🍔', 'color': '#f59e0b'},
    {'name': 'Transport',       'icon': '🚗', 'color': '#06b6d4'},
    {'name': 'Shopping',        'icon': '🛍️', 'color': '#ec4899'},
    {'name': 'Entertainment',   'icon': '🎬', 'color': '#8b5cf6'},
    {'name': 'Health',          'icon': '💊', 'color': '#10b981'},
    {'name': 'Utilities',       'icon': '💡', 'color': '#f97316'},
    {'name': 'Education',       'icon': '📚', 'color': '#6366f1'},
    {'name': 'Travel',          'icon': '✈️', 'color': '#14b8a6'},
    {'name': 'Rent',            'icon': '🏠', 'color': '#ef4444'},
    {'name': 'Salary',          'icon': '💰', 'color': '#22c55e'},
    {'name': 'Freelance',       'icon': '💻', 'color': '#a78bfa'},
    {'name': 'Investment',      'icon': '📈', 'color': '#84cc16'},
    {'name': 'Other',           'icon': '📂', 'color': '#6b7280'},
]


def seed_categories() -> None:
    """Insert default categories if the table is empty."""
    if Category.query.count() == 0:
        for cat in DEFAULT_CATEGORIES:
            db.session.add(Category(**cat))
        db.session.commit()
