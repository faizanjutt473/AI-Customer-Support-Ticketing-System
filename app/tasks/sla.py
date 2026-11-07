from datetime import datetime, timezone

from celery import shared_task

from app.extensions import db
from app.models import Ticket, User, Notification
from app.services.notify import push


@shared_task(ignore_result=True)
def check_sla_breaches():
    """Notifies the assigned agent and all admins once when a ticket passes its SLA deadline."""
    now = datetime.now(timezone.utc)
    tickets = Ticket.query.filter(
        Ticket.status != "Closed",
        Ticket.sla_due_at.isnot(None),
        Ticket.sla_due_at < now,
        Ticket.sla_breach_notified.is_(False),
    ).all()

    admins = User.query.filter_by(role="admin").all()
    notes = []
    for t in tickets:
        recipients = {u.id: u for u in admins}
        if t.agent is not None:
            recipients[t.agent.id] = t.agent
        for u in recipients.values():
            note = Notification(
                user_id=u.id,
                ticket_id=t.id,
                text=f"SLA breached: ticket #{t.id} {t.subject}",
            )
            db.session.add(note)
            notes.append(note)
        t.sla_breach_notified = True

    db.session.commit()
    for note in notes:
        push(note)
    return len(tickets)