"""
ai_service.py — Gemini AI integration with smart contextual intelligence for Finora AI.
"""

import os
import json
import re
import urllib.request
import ssl
from typing import Optional

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = (
    "You are Finora AI, a smart personal finance assistant. "
    "Your job is to help users with budgeting, expense tracking, saving tips, "
    "and general financial advice tailored to the Indian market. "
    "Be concise, friendly, and always use Indian Rupee (₹) for monetary amounts. "
    "When you give advice, make it actionable and specific with bullet points. "
    "Use the user's actual transactions and budgets provided in context."
)


def _call_gemini_api(prompt: str, api_key: str, timeout: int = 5) -> Optional[str]:
    """Call Google Gemini API via lightweight HTTP request with fast timeout."""
    if not api_key or api_key == 'your-gemini-api-key-here':
        return None

    ctx = ssl.create_default_context()
    models = ['gemini-3.8-flash', 'gemini-flash-latest', 'gemini-2.5-flash']

    payload = json.dumps({
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {
            'temperature': 0.7,
            'maxOutputTokens': 400,
        }
    }).encode('utf-8')

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=timeout) as res:
                data = json.loads(res.read().decode('utf-8'))
                candidates = data.get('candidates', [])
                if candidates:
                    parts = candidates[0].get('content', {}).get('parts', [])
                    if parts and 'text' in parts[0]:
                        return parts[0]['text'].strip()
        except Exception:
            continue

    return None


def _generate_dynamic_financial_response(
    query: str,
    transactions: Optional[list[dict]] = None,
    budgets: Optional[list[dict]] = None
) -> str:
    """
    Generate a dynamic, highly specific financial response based on the
    user's exact question and their actual financial data.
    """
    q = query.lower().strip()
    txns = transactions or []
    bgts = budgets or []

    # Calculate real-time stats
    expenses = [t for t in txns if t.get('type') == 'expense']
    incomes = [t for t in txns if t.get('type') == 'income']

    total_expense = sum(float(t.get('amount', 0)) for t in expenses)
    total_income = sum(float(t.get('amount', 0)) for t in incomes)
    net_savings = total_income - total_expense
    savings_rate = round((net_savings / total_income * 100), 1) if total_income > 0 else 0

    # Category breakdown
    cat_totals: dict[str, float] = {}
    for t in expenses:
        cat = t.get('category', 'Other')
        cat_totals[cat] = cat_totals.get(cat, 0.0) + float(t.get('amount', 0))

    top_cat = max(cat_totals, key=cat_totals.__getitem__) if cat_totals else "None"
    top_amt = cat_totals.get(top_cat, 0.0)

    # 1. Greetings / Introduction
    if any(q.startswith(w) for w in ['hi', 'hello', 'hey', 'greetings', 'namaste']) or q in ['who are you', 'help']:
        return (
            "Hello! 👋 I am your Finora AI Financial Advisor.\n\n"
            f"Here is your current financial pulse:\n"
            f"• Total Income: ₹{total_income:,.0f}\n"
            f"• Total Expenses: ₹{total_expense:,.0f}\n"
            f"• Net Savings: ₹{net_savings:,.0f} ({savings_rate}% savings rate)\n\n"
            "You can ask me questions like:\n"
            "• 'How much did I spend on food or Swiggy?'\n"
            "• 'How are my monthly budgets looking?'\n"
            "• 'What is my highest spending category?'\n"
            "• 'Tips to increase my savings rate to 30%'"
        )

    # 2. Food / Dining / Delivery queries
    if any(w in q for w in ['food', 'dining', 'swiggy', 'zomato', 'restaurant', 'lunch', 'dinner', 'eat']):
        food_txns = [t for t in expenses if 'food' in str(t.get('category', '')).lower() or any(k in str(t.get('merchant', '')).lower() for k in ['swiggy', 'zomato', 'restaurant', 'food'])]
        food_sum = sum(float(t.get('amount', 0)) for t in food_txns)
        food_pct = round((food_sum / total_expense * 100), 1) if total_expense > 0 else 0
        merchants = ", ".join(set(t.get('merchant', 'Food') for t in food_txns[:4])) or "Swiggy, Zomato"
        return (
            f"🍔 Food & Dining Breakdown:\n\n"
            f"• Total Spent: ₹{food_sum:,.0f} ({food_pct}% of your total expenses)\n"
            f"• Recent Merchants: {merchants}\n"
            f"• Activity: {len(food_txns)} transactions recorded this month.\n\n"
            f"💡 Actionable Advice:\n"
            f"1. Cap food delivery to 2 orders per week to save approximately ₹1,500–2,000 monthly.\n"
            f"2. Check out your Food & Dining budget card to ensure you stay under your monthly limit."
        )

    # 3. Shopping / E-commerce queries
    if any(w in q for w in ['shopping', 'amazon', 'flipkart', 'myntra', 'clothes', 'purchase']):
        shop_txns = [t for t in expenses if 'shop' in str(t.get('category', '')).lower() or any(k in str(t.get('merchant', '')).lower() for k in ['amazon', 'flipkart', 'myntra'])]
        shop_sum = sum(float(t.get('amount', 0)) for t in shop_txns)
        return (
            f"🛍️ Shopping Summary:\n\n"
            f"• Total Spent: ₹{shop_sum:,.0f} across {len(shop_txns)} orders.\n"
            f"• Recent Purchases: {', '.join(t.get('merchant','Shop') for t in shop_txns[:3]) or 'Amazon, Myntra'}\n\n"
            f"💡 Smart Rule:\n"
            f"Apply the 48-Hour Cart Rule: wait two full days before checking out non-essential online items. Over 60% of impulse purchases are avoided this way!"
        )

    # 4. Travel / Transport / Commute queries
    if any(w in q for w in ['travel', 'transport', 'uber', 'ola', 'rapido', 'cab', 'metro', 'petrol', 'fuel']):
        travel_txns = [t for t in expenses if 'transport' in str(t.get('category', '')).lower() or any(k in str(t.get('merchant', '')).lower() for k in ['uber', 'ola', 'rapido', 'metro'])]
        travel_sum = sum(float(t.get('amount', 0)) for t in travel_txns)
        return (
            f"🚗 Transport & Travel Breakdown:\n\n"
            f"• Total Spent: ₹{travel_sum:,.0f} this month.\n"
            f"• Rides logged: {len(travel_txns)} trips (including Uber/Rapido).\n\n"
            f"💡 Commute Tip:\n"
            f"Opting for public metro or shared rides for predictable commutes can reduce transport costs by ~30%."
        )

    # 5. Salary / Income queries
    if any(w in q for w in ['salary', 'income', 'earning', 'credited', 'make']):
        return (
            f"💰 Income & Earnings Overview:\n\n"
            f"• Total Inflow: ₹{total_income:,.0f}\n"
            f"• Inflow Sources: {', '.join(t.get('merchant', 'Employer') for t in incomes) or 'Monthly Salary'}\n"
            f"• Net Balance After Expenses: ₹{net_savings:,.0f}\n\n"
            f"💡 Recommended 50/30/20 Rule for ₹{total_income:,.0f}:\n"
            f"• Needs (50%): ₹{total_income * 0.5:,.0f}\n"
            f"• Wants (30%): ₹{total_income * 0.3:,.0f}\n"
            f"• Savings & Investment (20%): ₹{total_income * 0.2:,.0f}"
        )

    # 6. Budget status queries
    if any(w in q for w in ['budget', 'limit', 'threshold', 'planner', 'target']):
        if bgts:
            lines = []
            for b in bgts[:5]:
                cat = b.get('category', 'Category')
                spent = float(b.get('spent_amount', 0))
                limit = float(b.get('limit_amount', 1))
                pct = round((spent / limit * 100), 1) if limit > 0 else 0
                status_icon = "⚠️" if pct >= 80 else "✅"
                lines.append(f"• {status_icon} {cat}: ₹{spent:,.0f} / ₹{limit:,.0f} ({pct}% used)")
            bgt_summary = "\n".join(lines)
        else:
            bgt_summary = "• No custom category budgets configured yet. Visit the Budgets tab to set spending targets!"

        return (
            f"🎯 Monthly Budget Status:\n\n"
            f"{bgt_summary}\n\n"
            f"💡 Recommendation:\n"
            f"Keep all categories under 80% utilization before the 20th of the month to avoid end-of-month budget stress."
        )

    # 7. Savings / Investments / Wealth
    if any(w in q for w in ['save', 'saving', 'invest', 'sip', 'wealth', 'emergency fund']):
        monthly_invest_rec = round(total_income * 0.2) if total_income > 0 else 5000
        return (
            f"📈 Wealth & Savings Strategy:\n\n"
            f"• Your current savings: ₹{net_savings:,.0f} ({savings_rate}% of income)\n"
            f"• Target Monthly SIP: ₹{monthly_invest_rec:,.0f} (20% of income)\n"
            f"• Emergency Fund Goal: 3 months of basic expenses = ₹{total_expense * 3:,.0f}\n\n"
            f"💡 Action Plan:\n"
            f"1. Set up an automated mutual fund SIP scheduled 1 day after your salary credit.\n"
            f"2. Keep emergency reserves in an accessible high-yield savings account or liquid fund."
        )

    # 8. Highest Expense / Spending Analysis
    if any(w in q for w in ['highest', 'most', 'biggest', 'largest', 'spending breakdown', 'analysis', 'expenses']):
        top_items = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)[:4]
        items_str = "\n".join(f"• {cat}: ₹{amt:,.0f} ({round(amt/total_expense*100, 1)}%)" for cat, amt in top_items) if top_items else "No expenses yet."
        return (
            f"🔍 Spending Breakdown & Highlights:\n\n"
            f"• Total Outflow: ₹{total_expense:,.0f}\n"
            f"• Top Category: {top_cat} (₹{top_amt:,.0f})\n\n"
            f"Top Categories:\n{items_str}\n\n"
            f"💡 Focus Area:\n"
            f"Trimming your spending in '{top_cat}' by just 15% will instantly free up ₹{top_amt * 0.15:,.0f} for your monthly savings!"
        )

    # 9. Affordability question ("can I afford X?")
    if any(w in q for w in ['can i buy', 'can i afford', 'should i buy', 'afford']):
        # Extract potential amount from query
        amt_match = re.search(r'(?:rs\.?|₹|inr)?\s*([\d,]+)', q)
        desired_amt = float(amt_match.group(1).replace(',', '')) if amt_match else 2000
        can_afford = net_savings >= desired_amt
        return (
            f"🤔 Affordability Check for ₹{desired_amt:,.0f}:\n\n"
            f"• Current Net Monthly Savings: ₹{net_savings:,.0f}\n"
            f"• Status: {'✅ Affordable' if can_afford else '⚠️ Stretch / Delay Recommended'}\n\n"
            f"💡 Guidance:\n"
            f"{'You have sufficient room in this month’s savings without disrupting your core expenses.' if can_afford else 'Purchasing this now will reduce your monthly savings below safe reserves. Consider budgeting for it next month.'}"
        )

    # 10. Default General Intelligent Advice
    return (
        f"💡 Finora Financial Advice for: \"{query}\"\n\n"
        f"Based on your profile (Income: ₹{total_income:,.0f}, Expenses: ₹{total_expense:,.0f}):\n"
        f"1. Your current net surplus is ₹{net_savings:,.0f} ({savings_rate}% savings rate).\n"
        f"2. Your largest spending category is {top_cat} (₹{top_amt:,.0f}).\n"
        f"3. Recommendation: Automate a 10% reduction in discretionary spending to boost your emergency cushion by ₹{total_expense * 0.1:,.0f} every month.\n\n"
        f"Feel free to ask specific questions about your food expenses, shopping, salary, or budget limits!"
    )


def get_financial_advice(
    user_message: str,
    user_context: Optional[str] = None,
    api_key: Optional[str] = None,
    transactions: Optional[list[dict]] = None,
    budgets: Optional[list[dict]] = None,
) -> dict:
    """
    Provide intelligent financial advice.
    Attempts live Gemini API first; falls back seamlessly to dynamic local intelligence.
    """
    raw_key = (api_key or os.getenv('GEMINI_API_KEY', '')).strip().strip('"').strip("'")

    # 1. If key is configured, try live Gemini API with 4s timeout
    if raw_key and raw_key != 'your-gemini-api-key-here':
        prompt = f"{_SYSTEM_PROMPT}\n\nContext:\n{user_context or ''}\n\nUser Question: {user_message}\nAnswer:"
        gemini_reply = _call_gemini_api(prompt, raw_key, timeout=4)
        if gemini_reply:
            return {'success': True, 'reply': gemini_reply, 'error': None}

    # 2. Dynamic, context-driven financial intelligence engine
    dynamic_reply = _generate_dynamic_financial_response(user_message, transactions, budgets)
    return {'success': True, 'reply': dynamic_reply, 'error': None}


def get_spending_insight(transactions: list[dict]) -> str:
    """
    Analyse a list of transaction dicts and return a one-sentence insight.
    """
    if not transactions:
        return "No recent transactions to analyse."

    expenses = [t for t in transactions if t.get('type') == 'expense']
    if not expenses:
        return "No expense transactions found."

    from collections import defaultdict
    by_cat: dict[str, float] = defaultdict(float)
    for t in expenses:
        by_cat[t.get('category', 'Other')] += float(t.get('amount', 0))

    if not by_cat:
        return "Keep tracking your expenses to unlock AI insights."

    top_cat = max(by_cat, key=by_cat.__getitem__)
    top_amt = by_cat[top_cat]
    total = sum(by_cat.values())
    pct = round((top_amt / total * 100), 1) if total else 0

    return f"Your biggest expense category is {top_cat} at ₹{top_amt:,.0f} ({pct}% of total spending)."


def build_user_context(transactions: list[dict], budgets: list[dict]) -> str:
    """Build a compact text context string for the AI prompt."""
    lines = []

    if transactions:
        lines.append("Recent transactions:")
        for t in transactions[:15]:
            lines.append(
                f"  {t.get('type','?').upper()} ₹{float(t.get('amount',0)):,.0f}"
                f" — {t.get('category','?')} at {t.get('merchant','?')} ({t.get('date','?')})"
            )

    if budgets:
        lines.append("\nMonthly budgets:")
        for b in budgets:
            pct = b.get('percentage_used', 0)
            lines.append(
                f"  {b.get('category','?')}: ₹{float(b.get('spent_amount',0)):,.0f}"
                f" / ₹{float(b.get('limit_amount',0)):,.0f} ({pct}% used)"
            )

    return "\n".join(lines) if lines else "No financial data available."
