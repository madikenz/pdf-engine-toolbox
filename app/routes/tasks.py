"""Task status polling endpoint.

Heavy operations return a task_id. Clients poll this endpoint to check progress.
"""

from fastapi import APIRouter

from app.services import task_service

router = APIRouter()


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get the status of a background task."""
    task = task_service.get_task(task_id)
    if task is None:
        return {"success": False, "error": {"code": "TASK_NOT_FOUND", "message": f"Task {task_id} not found"}}

    return {"success": True, "data": task.to_dict()}
