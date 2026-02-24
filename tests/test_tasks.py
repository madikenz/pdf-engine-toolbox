"""Test background task polling endpoint."""

from app.services import task_service


def test_get_task_not_found(client):
    """Requesting a non-existent task should return an error."""
    response = client.get("/tasks/nonexistent-id")
    data = response.json()
    assert data["success"] is False


def test_task_lifecycle(client):
    """Create, process, and complete a task."""
    task = task_service.create_task("test_op")
    assert task.status == task_service.TaskStatus.PENDING

    # Poll - should show pending
    response = client.get(f"/tasks/{task.id}")
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "pending"

    # Mark processing
    task_service.set_processing(task.id)
    response = client.get(f"/tasks/{task.id}")
    assert response.json()["data"]["status"] == "processing"

    # Complete
    task_service.complete_task(task.id, {"pages_processed": 10})
    response = client.get(f"/tasks/{task.id}")
    data = response.json()["data"]
    assert data["status"] == "completed"
    assert data["result"]["pages_processed"] == 10


def test_task_failure(client):
    """Failed tasks should report the error."""
    task = task_service.create_task("failing_op")
    task_service.fail_task(task.id, "Something went wrong")

    response = client.get(f"/tasks/{task.id}")
    data = response.json()["data"]
    assert data["status"] == "failed"
    assert "Something went wrong" in data["error"]
