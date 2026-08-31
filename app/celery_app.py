from app.core.config import settings
from celery import Celery

celery_app = Celery(
    "simple_sim_platform",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.simulation_tasks"
    ]
)

celery_app.conf.update(
    task_track_started=True,
    task_time_limit=600,
    task_soft_time_limit=480,
    worker_prefetch_multiplier=1
)