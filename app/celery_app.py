from celery import Celery

from app.config import settings

celery_app = Celery(
    "ai_interviewer",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks"],
)
