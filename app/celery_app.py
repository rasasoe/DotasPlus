from celery import Celery
from app.config import settings

celery_app = Celery(
    "dotas_plus",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.task_routes = {
    "app.tasks.crawl_source": {"queue": "crawl"},
    "app.tasks.normalize_document": {"queue": "normalize"},
    "app.tasks.match_incident": {"queue": "match"},
    "app.tasks.send_alert": {"queue": "alert"},
}
