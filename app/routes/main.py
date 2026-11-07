from datetime import datetime, timedelta, timezone

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from sqlalchemy import func, or_

from app.extensions import db
from app.models import Ticket, Notification, Customer, Message, User, SLAPolicy, KBArticle
from app.services.classifier import analyze
from app.services.rag import retrieve, draft_reply, llm_reply
from app.services.notify import push

main_bp = Blueprint("main", __name__)


def sla_info(t):
    """Returns (label, css class) for a ticket's SLA badge."""
    if t.status == "Closed":
        return "Met", "OK"
    h = t.hours_left
    if h is None:
        return "No SLA", "Normal"
    if h < 0:
        return "Breached", "Breached"
    if h < 1:
        return f"{int(h * 60)} min left", "Risk"
    if h <= 3:
        return f"{h:.0f}h left", "Risk"
    return f"{h:.0f}h left", "OK"


@main_bp.app_context_processor
def inject_globals():
    unread = 0
    if current_user.is_authenticated:
        unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return {"unread_count": unread, "sla_info": sla_info}


@main_bp.route("/dashboard")
@login_required
def dashboard():
    now = datetime.now(timezone.utc)
    open_q = Ticket.query.filter(Ticket.status != "Closed")

    open_count = open_q.count()
    urgent = (
        open_q.filter(or_(Ticket.priority == "Urgent", Ticket.sentiment == "Angry"))
        .order_by(Ticket.created_at.desc())
        .all()
    )
    at_risk = (
        open_q.filter(Ticket.sla_due_at <= now + timedelta(hours=3))
        .order_by(Ticket.sla_due_at)
        .all()
    )

    rows = dict(
        db.session.query(Ticket.category, func.count(Ticket.id)).group_by(Ticket.category).all()
    )
    total = sum(rows.values()) or 1
    categories = [(c, rows.get(c, 0), rows.get(c, 0) / total * 100) for c in ("Billing", "Technical", "Refund")]

    closed = Ticket.query.filter_by(status="Closed").all()
    met = sum(1 for t in closed if t.closed_at and t.sla_due_at and t.closed_at <= t.sla_due_at)
    sla_pct = round(met / len(closed) * 100) if closed else 100

    return render_template(
        "dashboard.html",
        open_count=open_count,
        urgent=urgent,
        at_risk=at_risk,
        categories=categories,
        sla_pct=sla_pct,
    )

@main_bp.route("/tickets")
@login_required
def tickets():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    category = request.args.get("category", "")
    priority = request.args.get("priority", "")

    query = Ticket.query.join(Customer)

    if q:
        conditions = [Ticket.subject.ilike(f"%{q}%"), Customer.name.ilike(f"%{q}%")]
        if q.lstrip("#").isdigit():
            conditions.append(Ticket.id == int(q.lstrip("#")))
        query = query.filter(or_(*conditions))
    if status:
        query = query.filter(Ticket.status == status)
    if category:
        query = query.filter(Ticket.category == category)
    if priority:
        query = query.filter(Ticket.priority == priority)

    return render_template(
        "tickets.html",
        tickets=query.order_by(Ticket.created_at.desc()).all(),
        q=q, status=status, category=category, priority=priority,
        statuses=["Open", "In progress", "Closed"],
        categories=["Billing", "Technical", "Refund"],
        priorities=["Urgent", "High", "Normal", "Low"],
    ) 


@main_bp.route("/tickets/<int:ticket_id>")
@login_required
def ticket_detail(ticket_id):
    ticket = db.get_or_404(Ticket, ticket_id)
    try:
        articles = [a for a, _ in retrieve(f"{ticket.subject}. {ticket.description}")]
    except Exception:
        articles = []  # e.g. embedding model could not load; the page must still open
    return render_template(
        "ticket_detail.html",
        ticket=ticket,
        agents=User.query.order_by(User.name).all(),
        suggestions=articles,
        draft=draft_reply(ticket, articles),
    )


@main_bp.route("/tickets/<int:ticket_id>/reply", methods=["POST"])
@login_required
def ticket_reply(ticket_id):
    ticket = db.get_or_404(Ticket, ticket_id)
    body = request.form.get("body", "").strip()
    if not body or ticket.status == "Closed":
        return redirect(url_for("main.ticket_detail", ticket_id=ticket.id))

    db.session.add(
        Message(ticket_id=ticket.id, sender_type="agent", user_id=current_user.id, body=body)
    )
    if ticket.first_response_at is None:
        ticket.first_response_at = datetime.now(timezone.utc)
    if ticket.status == "Open":
        ticket.status = "In progress"
    if ticket.agent_id is None:
        ticket.agent_id = current_user.id
    db.session.commit()
    flash("Reply sent.")
    return redirect(url_for("main.ticket_detail", ticket_id=ticket.id))


@main_bp.route("/tickets/<int:ticket_id>/assign", methods=["POST"])
@login_required
def ticket_assign(ticket_id):
    ticket = db.get_or_404(Ticket, ticket_id)
    agent_id = request.form.get("agent_id", "")
    note = None

    if agent_id.isdigit():
        agent = db.session.get(User, int(agent_id))
        if agent is None:
            return redirect(url_for("main.ticket_detail", ticket_id=ticket.id))
        ticket.agent_id = agent.id
        if ticket.status == "Open":
            ticket.status = "In progress"
        if agent.id != current_user.id:
            note = Notification(
                user_id=agent.id,
                ticket_id=ticket.id,
                text=f"Ticket #{ticket.id} was assigned to you",
            )
            db.session.add(note)
        flash(f"Assigned to {agent.name}.")
    else:
        ticket.agent_id = None
        flash("Ticket is now unassigned.")

    db.session.commit()
    if note:
        push(note)
    return redirect(url_for("main.ticket_detail", ticket_id=ticket.id))


@main_bp.route("/tickets/<int:ticket_id>/close", methods=["POST"])
@login_required
def ticket_close(ticket_id):
    ticket = db.get_or_404(Ticket, ticket_id)
    if ticket.status != "Closed":
        ticket.status = "Closed"
        ticket.closed_at = datetime.now(timezone.utc)
        db.session.commit()
        flash(f"Ticket #{ticket.id} closed.")
    return redirect(url_for("main.ticket_detail", ticket_id=ticket.id))

@main_bp.route("/api/analyze", methods=["POST"])
@login_required
def api_analyze():
    data = request.get_json(silent=True) or {}
    try:
        result = analyze(data.get("subject", ""), data.get("description", ""))
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 503
    return jsonify(result or {})


@main_bp.route("/tickets/new", methods=["GET", "POST"])
@login_required
def ticket_new():
    if request.method == "GET":
        return render_template("ticket_new.html", form={})

    name = request.form.get("customer", "").strip()
    email = request.form.get("email", "").strip().lower() or None
    subject = request.form.get("subject", "").strip()
    description = request.form.get("description", "").strip()

    if not (name and subject and description):
        flash("Please fill in the customer name, subject and message.")
        return render_template("ticket_new.html", form=request.form)

    customer = None
    if email:
        customer = Customer.query.filter_by(email=email).first()
    if customer is None:
        customer = Customer.query.filter(Customer.name.ilike(name)).first()
    if customer is None:
        customer = Customer(name=name, email=email)
        db.session.add(customer)
        db.session.flush()

    try:
        ai = analyze(subject, description)
    except FileNotFoundError:
        ai = None
    ai = ai or {"category": "Technical", "priority": "Normal", "sentiment": "Neutral", "confidence": None}

    policy = SLAPolicy.query.filter_by(priority=ai["priority"]).first()
    hours = policy.response_hours if policy else 12

    ticket = Ticket(
        subject=subject,
        description=description,
        category=ai["category"],
        priority=ai["priority"],
        sentiment=ai["sentiment"],
        confidence=ai["confidence"],
        status="Open",
        customer_id=customer.id,
        sla_due_at=datetime.now(timezone.utc) + timedelta(hours=hours),
    )
    db.session.add(ticket)
    db.session.flush()

    db.session.add(Message(ticket_id=ticket.id, sender_type="customer", body=description))

    new_notes = []
    if ai["priority"] == "Urgent" or ai["sentiment"] == "Angry":
        for user in User.query.all():
            if user.id == current_user.id:
                continue  # the creator already knows
            note = Notification(
                user_id=user.id,
                ticket_id=ticket.id,
                text=f"New urgent ticket #{ticket.id}: {subject}",
            )
            db.session.add(note)
            new_notes.append(note)

    db.session.commit()
    for note in new_notes:
        push(note)

    flash(f"Ticket #{ticket.id} created and sorted by AI.")
    return redirect(url_for("main.ticket_detail", ticket_id=ticket.id))  

@main_bp.route("/knowledge-base")
@login_required
def knowledge_base():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "")

    query = KBArticle.query
    if q:
        query = query.filter(or_(KBArticle.title.ilike(f"%{q}%"), KBArticle.body.ilike(f"%{q}%")))
    if category:
        query = query.filter(KBArticle.category == category)

    return render_template(
        "knowledge_base.html",
        articles=query.order_by(KBArticle.title).all(),
        q=q,
        category=category,
        categories=["Billing", "Technical", "Refund"],
    )


@main_bp.route("/agents")
@login_required
def agents():
    now = datetime.now(timezone.utc)

    def sla_pct(tickets):
        # A ticket counts once it is closed, or already past its deadline
        measured = [t for t in tickets if t.sla_due_at and (t.status == "Closed" or t.sla_due_at < now)]
        met = [t for t in measured if t.status == "Closed" and t.closed_at and t.closed_at <= t.sla_due_at]
        return round(len(met) / len(measured) * 100) if measured else None

    rows = []
    for u in User.query.order_by(User.name).all():
        tickets = Ticket.query.filter_by(agent_id=u.id).all()
        replies = [
            (t.first_response_at - t.created_at).total_seconds() / 60
            for t in tickets
            if t.first_response_at and t.created_at
        ]
        rows.append(
            {
                "name": u.name,
                "open": sum(1 for t in tickets if t.status != "Closed"),
                "resolved": sum(1 for t in tickets if t.status == "Closed"),
                "avg_reply": round(sum(replies) / len(replies)) if replies else None,
                "sla_pct": sla_pct(tickets),
            }
        )

    policies = []
    for p in SLAPolicy.query.order_by(SLAPolicy.response_hours).all():
        policies.append(
            {
                "priority": p.priority,
                "response_hours": p.response_hours,
                "pct": sla_pct(Ticket.query.filter_by(priority=p.priority).all()),
            }
        )

    return render_template("agents.html", rows=rows, policies=policies)


@main_bp.route("/notifications")
@login_required
def notifications():
    items = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )
    return render_template("notifications.html", notifications=items)


@main_bp.route("/notifications/<int:notification_id>/open")
@login_required
def notification_open(notification_id):
    n = db.get_or_404(Notification, notification_id)
    if n.user_id != current_user.id:
        abort(404)
    n.is_read = True
    db.session.commit()
    if n.ticket_id:
        return redirect(url_for("main.ticket_detail", ticket_id=n.ticket_id))
    return redirect(url_for("main.notifications"))


@main_bp.route("/notifications/read-all", methods=["POST"])
@login_required
def notifications_read_all():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return redirect(url_for("main.notifications"))  

@main_bp.route("/tickets/<int:ticket_id>/ai-reply", methods=["POST"])
@login_required
def ticket_ai_reply(ticket_id):
    ticket = db.get_or_404(Ticket, ticket_id)
    try:
        articles = [a for a, _ in retrieve(f"{ticket.subject}. {ticket.description}")]
    except Exception as e:
        return jsonify({"error": f"Search failed: {type(e).__name__}"}), 500
    text, error = llm_reply(ticket, articles)
    if error:
        return jsonify({"error": error}), 503
    return jsonify({"reply": text, "sources": [a.title for a in articles]})   