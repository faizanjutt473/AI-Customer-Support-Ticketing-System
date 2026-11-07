from datetime import datetime, timedelta, timezone

from app import create_app
from app.extensions import db
from app.models import (
    User, Customer, Ticket, Message, KBArticle, Notification, SLAPolicy,
)

app = create_app()
now = datetime.now(timezone.utc)

SLA = [("Urgent", 1), ("High", 4), ("Normal", 12), ("Low", 24)]

AGENTS = [
    ("Ayesha Khan", "ayesha@supportdesk.pk", "admin"),
    ("Bilal Ahmed", "bilal@supportdesk.pk", "agent"),
    ("Hina Malik", "hina@supportdesk.pk", "agent"),
    ("Usman Tariq", "usman@supportdesk.pk", "agent"),
    ("Sara Iqbal", "sara@supportdesk.pk", "agent"),
]

KB = [
    ("How to request a refund", "Refund",
     "Refunds go back to the original payment method within 5-7 business days. Purchases are eligible within 30 days."),
    ("Fix a double charge", "Billing",
     "If you were charged twice, the duplicate is reversed automatically in 3 business days. Share both transaction IDs so we can confirm."),
    ("Reset your password", "Technical",
     "Use 'Forgot password' on the login page. Reset links expire after 30 minutes. Locked accounts unlock after 15 minutes."),
    ("App crashes on startup", "Technical",
     "Update to the latest version, clear the cache and restart. If it still crashes, send the error code and device model."),
    ("Update billing details", "Billing",
     "Go to Account > Billing to change your card, address or invoice email. Changes apply from the next invoice."),
    ("Cancel a subscription", "Refund",
     "Cancel anytime from Account > Plan. Access continues until the end of the paid period."),
]

# subject, customer, message, category, priority, sentiment, status, agent, hours_left, hours_ago
TICKETS = [
    ("Cannot login, account locked", "Mehran Textiles",
     "I have a client demo in an hour and my account is locked. This is unacceptable, fix it immediately!",
     "Technical", "Urgent", "Angry", "Open", None, 1, 0.5),
    ("Refund for annual plan", "Noor Foods",
     "Please refund my annual plan, I cancelled within a week of buying.",
     "Refund", "High", "Neutral", "In progress", "Hina Malik", 5, 1.5),
    ("Charged twice for March invoice", "Zain Traders",
     "My card was charged twice for the March invoice. Please check the payment.",
     "Billing", "High", "Negative", "In progress", "Ayesha Khan", 3, 2),
    ("App crashes on startup", "Dr. Imran Clinic",
     "The app crashes every time I open it after the update. Error code 502.",
     "Technical", "High", "Neutral", "Open", "Bilal Ahmed", -1, 6),
    ("Change invoice email", "Pak Logistics",
     "Please change our invoice email address to accounts@paklogistics.pk. Thank you!",
     "Billing", "Low", "Positive", "Closed", "Sara Iqbal", 20, 26),
    ("Worst service, nobody replies", "Rana Electronics",
     "Terrible support. I am fed up, nobody replies to my payment issue. This is a scam.",
     "Billing", "Urgent", "Angry", "Open", "Usman Tariq", 0.5, 27),
    ("Slow dashboard loading", "Lahore Pharma",
     "The dashboard is slow in the morning. Not urgent but please look into it.",
     "Technical", "Normal", "Neutral", "In progress", "Bilal Ahmed", 12, 50),
    ("Cancel subscription", "Hassan Studio",
     "How do I cancel my subscription? Great product, but we are closing the studio.",
     "Refund", "Low", "Positive", "Closed", "Hina Malik", 30, 52),
]

with app.app_context():
    if User.query.first():
        print("Database already has data. Seed skipped.")
        raise SystemExit

    for p, h in SLA:
        db.session.add(SLAPolicy(priority=p, response_hours=h))

    users = {}
    for name, email, role in AGENTS:
        u = User(name=name, email=email, role=role)
        u.set_password("demo1234")
        db.session.add(u)
        users[name] = u

    for title, cat, body in KB:
        db.session.add(KBArticle(title=title, category=cat, body=body))

    db.session.flush()

    first_ticket = None
    for subj, cust, msg, cat, pr, sent, status, agent, left, ago in TICKETS:
        customer = Customer(name=cust, email=cust.lower().replace(" ", "").replace(".", "") + "@example.com")
        db.session.add(customer)
        db.session.flush()

        created = now - timedelta(hours=ago)
        t = Ticket(
            subject=subj, description=msg, category=cat, priority=pr,
            sentiment=sent, confidence=88, status=status,
            customer_id=customer.id,
            agent_id=users[agent].id if agent else None,
            created_at=created,
            sla_due_at=now + timedelta(hours=left),
        )
        if status == "Closed":
            t.first_response_at = created + timedelta(hours=1)
            t.closed_at = created + timedelta(hours=3)
        elif status == "In progress":
            t.first_response_at = created + timedelta(minutes=40)
        db.session.add(t)
        db.session.flush()

        db.session.add(Message(ticket_id=t.id, sender_type="customer", body=msg, created_at=created))
        if status in ("In progress", "Closed"):
            db.session.add(Message(
                ticket_id=t.id, sender_type="agent", user_id=users[agent].id,
                body="Thanks for contacting us. We are looking into this and will update you shortly.",
                created_at=created + timedelta(minutes=40),
            ))
        if first_ticket is None:
            first_ticket = t

    ayesha = users["Ayesha Khan"]
    db.session.add(Notification(user_id=ayesha.id, ticket_id=first_ticket.id,
                                text="New urgent ticket flagged: angry customer", is_read=False))
    db.session.add(Notification(user_id=ayesha.id, ticket_id=first_ticket.id,
                                text="SLA breach: a ticket passed its deadline", is_read=False))
    db.session.add(Notification(user_id=ayesha.id, ticket_id=first_ticket.id,
                                text="A ticket was assigned to you", is_read=True))

    db.session.commit()
    print("Seed complete.")