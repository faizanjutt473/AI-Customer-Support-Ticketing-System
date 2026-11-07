from app.extensions import db


class SLAPolicy(db.Model):
    __tablename__ = "sla_policies"

    id = db.Column(db.Integer, primary_key=True)
    priority = db.Column(db.String(20), unique=True, nullable=False)
    response_hours = db.Column(db.Float, nullable=False)