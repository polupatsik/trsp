from fastapi import APIRouter, Depends, HTTPException
from app.schemas import TaskCreate, Task, StatusUpdate
from app.dependencies import get_current_user
from app.storage import tasks

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=Task, status_code=201)
def create_task(task: TaskCreate, user=Depends(get_current_user)):
    task_data = task.model_dump()
    task_data["id"] = len(tasks) + 1
    task_data["owner_id"] = user["id"]

    tasks.append(task_data)

    return task_data


@router.get("")
def get_tasks(
    status: str | None = None,
    min_priority: int | None = None,
    user=Depends(get_current_user)
):
    result = [t for t in tasks if t["owner_id"] == user["id"]]

    if status:
        result = [t for t in result if t["status"] == status]

    if min_priority:
        result = [t for t in result if t["priority"] >= min_priority]

    return result


@router.get("/{task_id}")
def get_task(task_id: int, user=Depends(get_current_user)):
    for task in tasks:
        if task["id"] == task_id and task["owner_id"] == user["id"]:
            return task

    raise HTTPException(status_code=404, detail="Task not found")


@router.patch("/{task_id}/status")
def update_status(task_id: int, payload: StatusUpdate, user=Depends(get_current_user)):
    for task in tasks:
        if task["id"] == task_id and task["owner_id"] == user["id"]:
            task["status"] = payload.status
            return task

    raise HTTPException(status_code=404, detail="Task not found")


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, user=Depends(get_current_user)):
    for task in tasks:
        if task["id"] == task_id and task["owner_id"] == user["id"]:
            tasks.remove(task)
            return

    raise HTTPException(status_code=404, detail="Task not found")
