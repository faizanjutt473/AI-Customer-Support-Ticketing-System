from datetime import datetime, timezone
from app.extensions import db

CATEGORIES = ["Billing", "Technical", "Refund"]
PRIORITIES = ["Low", "Normal", "High", "Urgent"]
SENTIMENTS = ["Positive", "Neutral", "Negative", "Angry"]
STATUSES = ["Open", "In progress", "Closed"]


class Ticket(db.Model):
    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)

    category = db.Column(db.String(20), default="Technical")
    priority = db.Column(db.String(20), default="Normal")
    sentiment = db.Column(db.String(20), default="Neutral")
    confidence = db.Column(db.Float, nullable=True)  # AI confidence (0-100)
    status = db.Column(db.String(20), default="Open", index=True)

    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    first_response_at = db.Column(db.DateTime(timezone=True), nullable=True)
    closed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    sla_due_at = db.Column(db.DateTime(timezone=True), nullable=True)
    sla_breach_notified = db.Column(db.Boolean, nullable=False, server_default=db.false())

    customer = db.relationship("Customer", back_populates="tickets")
    agent = db.relationship("User", backref="tickets")
    messages = db.relationship(
        "Message", back_populates="ticket",
        cascade="all, delete-orphan", order_by="Message.created_at",
    )

    @property
    def hours_left(self):
        if not self.sla_due_at:
            return None
        return (self.sla_due_at - datetime.now(timezone.utc)).total_seconds() / 3600