"""Deterministic SYNTHETIC bank operations tickets, not real customer data."""
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

CATEGORIES = {
    'Account Access': ('Digital Support', 8),
    'Card Dispute': ('Card Operations', 48),
    'Payment Investigation': ('Payments Operations', 24),
    'Account Maintenance': ('Client Services', 48),
    'Transfer Inquiry': ('Payments Operations', 24),
    'Document Verification': ('Client Services', 72),
}
PRIORITIES = ['Low', 'Medium', 'High', 'Critical']
START = datetime(2026, 8, 1, 9)

def generate(path: Path, n: int = 2600, seed: int = 42):
    rng = random.Random(seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    categories = list(CATEGORIES)
    rows = []
    for i in range(n):
        # Date distribution is deliberately not representative of a real bank.
        day = rng.randrange(98)
        created = START + timedelta(days=day, hours=rng.randrange(11), minutes=rng.randrange(60))
        # Intentionally inject a 2-week payments slowdown in the final period.
        incident = day >= 84
        cat = rng.choices(categories, weights=[18, 18, 19 if not incident else 37, 17, 14, 14], k=1)[0]
        team, sla_hours = CATEGORIES[cat]
        priority = rng.choices(PRIORITIES, weights=[18, 54, 23, 5], k=1)[0]
        if priority == 'Critical':
            sla_hours = min(sla_hours, 4)
        elif priority == 'High':
            sla_hours = min(sla_hours, 12)
        multiplier = rng.uniform(.18, 1.22)
        if incident and cat in ('Payment Investigation', 'Transfer Inquiry'):
            multiplier *= rng.uniform(1.45, 2.8)
        elapsed = round(sla_hours * multiplier, 2)
        # last ~7% remain open; evaluate age at an explicit analysis timestamp.
        open_case = (rng.random() < .07)
        resolved_at = None if open_case else created + timedelta(hours=elapsed)
        due_at = created + timedelta(hours=sla_hours)
        rows.append({
            'ticket_id': f'BO-{i+1:06d}',
            'created_at': created.isoformat(timespec='seconds'),
            'resolved_at': '' if resolved_at is None else resolved_at.isoformat(timespec='seconds'),
            'due_at': due_at.isoformat(timespec='seconds'),
            'category': cat,
            'team': team,
            'priority': priority,
            'channel': rng.choice(['Mobile App', 'Branch', 'Contact Centre', 'Online Banking']),
            'status': 'Open' if open_case else 'Resolved',
            'sla_target_hours': sla_hours,
            'synthetic_slowdown_flag': int(incident and cat in ('Payment Investigation', 'Transfer Inquiry')),
        })
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    return rows

if __name__ == '__main__':
    generate(Path('data/bank_service_tickets.csv'))
    print('Generated 2,600 synthetic service tickets')
