"""Background task tracking for long-running operations.

Heavy operations (OCR on 100 pages, deskew on large scans) can exceed
HTTP timeout limits. This module provides a simple in-memory task store
that lets the API:
  1. Accept a request and return a task_id immediately.
  2. Process in the background (via FastAPI BackgroundTasks).
  3. Let the client poll GET /tasks/{task_id} for status.
"""

import time
import uuid
from enum import Enum
from typing import Any

import structlog

log = structlog.get_logger()


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskInfo:
    """Holds state for a single background task."""

    __slots__ = ("id", "status", "result", "error", "created_at", "completed_at", "operation")

    def __init__(self, task_id: str, operation: str):
        self.id = task_id
        self.operation = operation
        self.status = TaskStatus.PENDING
        self.result: Any = None
        self.error: str | None = None
        self.created_at = time.time()
        self.completed_at: float | None = None

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "task_id": self.id,
            "status": self.status.value,
            "operation": self.operation,
            "created_at": self.created_at,
        }
        if self.completed_at:
            d["completed_at"] = self.completed_at
        if self.status == TaskStatus.COMPLETED and self.result is not None:
            d["result"] = self.result
        if self.status == TaskStatus.FAILED and self.error:
            d["error"] = self.error
        return d


# In-memory store (sufficient for single-process/App Runner).
# For multi-worker, swap to Redis.
_tasks: dict[str, TaskInfo] = {}

# Auto-prune completed tasks older than 1 hour
_MAX_AGE_SECONDS = 3600


def create_task(operation: str) -> TaskInfo:
    """Create and register a new background task."""
    _prune_old_tasks()
    task = TaskInfo(task_id=str(uuid.uuid4()), operation=operation)
    _tasks[task.id] = task
    log.info("task_created", task_id=task.id, operation=operation)
    return task


def get_task(task_id: str) -> TaskInfo | None:
    """Retrieve a task by ID."""
    return _tasks.get(task_id)


def complete_task(task_id: str, result: Any = None) -> None:
    """Mark a task as completed with optional result data."""
    task = _tasks.get(task_id)
    if task:
        task.status = TaskStatus.COMPLETED
        task.result = result
        task.completed_at = time.time()
        log.info("task_completed", task_id=task_id)


def fail_task(task_id: str, error: str) -> None:
    """Mark a task as failed with an error message."""
    task = _tasks.get(task_id)
    if task:
        task.status = TaskStatus.FAILED
        task.error = error
        task.completed_at = time.time()
        log.error("task_failed", task_id=task_id, error=error)


def set_processing(task_id: str) -> None:
    """Mark a task as actively processing."""
    task = _tasks.get(task_id)
    if task:
        task.status = TaskStatus.PROCESSING


def _prune_old_tasks() -> None:
    """Remove completed/failed tasks older than _MAX_AGE_SECONDS."""
    now = time.time()
    to_remove = [
        tid for tid, t in _tasks.items()
        if t.completed_at and (now - t.completed_at) > _MAX_AGE_SECONDS
    ]
    for tid in to_remove:
        del _tasks[tid]
