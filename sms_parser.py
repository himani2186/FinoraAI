"""
sms_parser.py — Enhanced SMS parser for Indian bank transaction SMS messages.
Used by both app.py API route and standalone utilities.
"""

import re
from datetime import date, datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Category keywords mapping
# ---------------------------------------------------------------------------
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    'Food & Dining':  ['swiggy', 'zomato', 'food', 'restaurant', 'cafe', 'dominos',
                       'pizza', 'kfc', 'mcdonalds', 'blinkit', 'dunzo', 'eatfit'],
    'Shopping':       ['amazon', 'flipkart', 'myntra', 'ajio', 'nykaa', 'meesho',
                       'snapdeal', 'shopping', 'store', 'mart'],
    'Transport':      ['uber', 'ola', 'rapido', 'petrol', 'fuel', 'diesel', 'metro',
                       'irctc', 'bus', 'auto', 'cab', 'parking', 'fastag'],
    'Entertainment':  ['netflix', 'spotify', 'hotstar', 'youtube', 'cinema', 'pvr',
                       'inox', 'bookmyshow', 'prime', 'zee5', 'sonyliv'],
    'Utilities':      ['electricity', 'water', 'gas', 'internet', 'wifi', 'broadband',
                       'airtel', 'jio', 'bsnl', 'vodafone', 'vi', 'tata', 'recharge',
                       'bill', 'postpaid', 'prepaid'],
    'Health':         ['hospital', 'pharmacy', 'medicine', 'doctor', 'clinic', 'apollo',
                       'medplus', 'practo', '1mg', 'netmeds'],
    'Education':      ['udemy', 'coursera', 'byju', 'unacademy', 'school', 'college',
                       'fees', 'tuition', 'books'],
    'Travel':         ['flight', 'hotel', 'oyo', 'makemytrip', 'goibibo', 'yatra',
                       'booking', 'airbnb'],
    'Salary':         ['salary', 'payroll', 'wages', 'stipend', 'ctc'],
    'Investment':     ['mutual fund', 'sip', 'stock', 'zerodha', 'groww', 'upstox',
                       'nse', 'bse', 'ipo'],
}

# ---------------------------------------------------------------------------
# Compiled regex patterns
# ---------------------------------------------------------------------------
_AMOUNT_PAT = re.compile(
    r'(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{1,2})?)',
    re.IGNORECASE,
)
_DEBIT_PAT = re.compile(
    r'\b(debited|debit|paid|spent|withdrawn|purchase|payment|sent|transferred to)\b',
    re.IGNORECASE,
)
_CREDIT_PAT = re.compile(
    r'\b(credited|credit|received|deposited|refund|cashback|received from|added)\b',
    re.IGNORECASE,
)
_MERCHANT_PAT = re.compile(
    r'(?:at|to|from|via|for|by)\s+([A-Za-z][A-Za-z0-9\s&\-\.\']{2,40}?)(?:\s+on|\s+for|\s*\.|,|$)',
    re.IGNORECASE,
)
# UPI-specific merchant pattern: "payment to Swiggy" / "paid to Zomato"
_UPI_MERCHANT_PAT = re.compile(
    r'(?:payment\s+to|paid\s+to|sent\s+to|transfer\s+to)\s+([A-Za-z0-9][A-Za-z0-9\s\-\.]{1,30}?)(?:\s*[@\.\s]|$)',
    re.IGNORECASE,
)
_ACCOUNT_PAT = re.compile(r'[Aa]/[Cc]\s*[Xx*]+(\d{4})|[Aa]cc(?:ount)?\s*[Xx*]+(\d{4})')
_DATE_PAT = re.compile(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})')
_UPI_PAT  = re.compile(r'UPI(?:\s*Ref(?:\s*No)?\.?\s*:?\s*)(\d+)', re.IGNORECASE)


def _infer_category(text: str) -> str:
    lower = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return category
    return 'Other'


def _clean_merchant(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    cleaned = raw.strip().strip('.,;')
    # Drop if it looks like a date/number
    if re.fullmatch(r'[\d\-/\.]+', cleaned):
        return None
    return cleaned[:60] if cleaned else None


def parse_sms(text: str) -> dict:
    """
    Parse an Indian bank / UPI transaction SMS.

    Returns
    -------
    dict with keys:
        raw, amount, merchant, type, category, date, account_last4,
        upi_ref, description, confidence ('high'|'medium'|'low')
    """
    result: dict = {
        'raw': text,
        'amount': None,
        'merchant': None,
        'type': None,
        'category': 'Other',
        'date': None,
        'account_last4': None,
        'upi_ref': None,
        'description': text[:120],
        'confidence': 'low',
    }

    # Amount
    amount_m = _AMOUNT_PAT.search(text)
    if amount_m:
        try:
            result['amount'] = float(amount_m.group(1).replace(',', ''))
        except ValueError:
            pass

    # Type
    if _DEBIT_PAT.search(text):
        result['type'] = 'expense'
    elif _CREDIT_PAT.search(text):
        result['type'] = 'income'

    # Merchant — try UPI-specific pattern first, fall back to generic
    upi_merch_m = _UPI_MERCHANT_PAT.search(text)
    if upi_merch_m:
        result['merchant'] = _clean_merchant(upi_merch_m.group(1))
    else:
        merchant_m = _MERCHANT_PAT.search(text)
        result['merchant'] = _clean_merchant(merchant_m.group(1) if merchant_m else None)

    # Date
    date_m = _DATE_PAT.search(text)
    if date_m:
        result['date'] = date_m.group(1)

    # Account last 4
    acc_m = _ACCOUNT_PAT.search(text)
    if acc_m:
        result['account_last4'] = acc_m.group(1) or acc_m.group(2)

    # UPI Ref
    upi_m = _UPI_PAT.search(text)
    if upi_m:
        result['upi_ref'] = upi_m.group(1)

    # Category
    result['category'] = _infer_category(text)

    # Confidence
    filled = sum(1 for k in ('amount', 'type', 'merchant') if result[k] is not None)
    result['confidence'] = 'high' if filled == 3 else ('medium' if filled >= 1 else 'low')

    return result


# ---------------------------------------------------------------------------
# CLI helper
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    import sys, json
    sms = ' '.join(sys.argv[1:]) or 'Rs. 500 debited from your account for UPI payment at Swiggy on 12-11-2024'
    print(json.dumps(parse_sms(sms), indent=2))
