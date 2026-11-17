import sys
sys.path.insert(0, r'C:\Users\HIMANI\.gemini\antigravity\scratch\finora-ai')
from sms_parser import parse_sms

tests = [
    'Rs.500 debited from your account for UPI payment to Swiggy on 14-11-2024',
    'Your A/c XXXX1234 debited INR 1200.00 for Amazon.in on 14-Nov-24. Ref: 123456',
    'Salary credited Rs.25000 to your account from HDFC Bank',
    'Uber ride booked. Rs 199 charged to your card ending 5678.',
]
for sms in tests:
    r = parse_sms(sms)
    print(f'SMS: {sms[:60]}...')
    print(f'  amount={r["amount"]}, merchant={r["merchant"]}, cat={r["category"]}, type={r["type"]}')
    print()
