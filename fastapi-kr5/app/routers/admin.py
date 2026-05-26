from collections import Counter
from fastapi import APIRouter, Depends, HTTPException
from app.dependencies import get_current_user
from app.storage import tasks

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(user=Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    return user


@router.get("/stats")
def stats(user=Depends(require_admin)):
    statuses = Counter(task["status"] for task in tasks)

    return {
        "total_tasks": len(tasks),
        "by_status": dict(statuses)
    }


@router.delete("/tasks/{task_id}")
def delete_any_task(task_id: int, user=Depends(require_admin)):
    for task in tasks:
        if task["id"] == task_id:
            tasks.remove(task)
            return {"message": "deleted"}

    raise HTTPException(status_code=404, detail="Task not found")
