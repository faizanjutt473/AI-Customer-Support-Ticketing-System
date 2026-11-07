from flask import Flask
from config import Config
from app.extensions import db, migrate, login_manager, socketio
from app.celery_app import celery_init_app


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    socketio.init_app(
        app,
        cors_allowed_origins="*",
        async_mode="threading",
        message_queue=app.config["REDIS_URL"],
    )
    celery_init_app(app)

    from app import models  # noqa: F401
    from app import sockets  # noqa: F401
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app