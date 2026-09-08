from fastapi import APIRouter

from app.celery_app import celery_app


router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}")
def read_task_status(task_id: str):
    task = celery_app.AsyncResult(task_id)
    payload = {
        "task_id": task_id,
        "state": task.state,
        "ready": task.ready(),
        "successful": task.successful() if task.ready() else None,
    }
    if task.ready():
        payload["result"] = str(task.result)
    return payload
