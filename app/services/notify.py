from app.extensions import socketio


def push(notification):
    """Send a saved notification to its owner in real time. Call after db.session.commit()."""
    socketio.emit(
        "notification",
        {
            "id": notification.id,
            "text": notification.text,
            "ticket_id": notification.ticket_id,
        },
        to=f"user_{notification.user_id}",
    )