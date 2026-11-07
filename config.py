import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    CELERY = dict(
        broker_url=REDIS_URL,
        result_backend=REDIS_URL,
        task_ignore_result=True,
        imports=("app.tasks.sla",),
        timezone="UTC",
        beat_schedule={
            "sla-breach-check": {
                "task": "app.tasks.sla.check_sla_breaches",
                "schedule": 60.0,  # every 60 seconds
            }
        },
    )