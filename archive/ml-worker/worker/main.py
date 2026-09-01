from celery import Celery
from worker.config import settings

app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["worker.tasks"]
)

app.conf.update(
    task_track_started=True,
    result_expires=3600,
)

if __name__ == '__main__':
    app.start()
