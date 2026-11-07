from flask_login import current_user
from flask_socketio import join_room

from app.extensions import socketio


@socketio.on("connect")
def on_connect():
    if not current_user.is_authenticated:
        return False  # reject anonymous connections
    join_room(f"user_{current_user.id}")