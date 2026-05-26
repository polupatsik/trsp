from fastapi import Header, HTTPException
from .storage import tasks


def get_current_user(
    x_user_id: str = Header(None),
    x_user_role: str = Header(default="user")
):
    if x_user_id is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        user_id = int(x_user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return {
        "id": user_id,
        "role": x_user_role
    }


def require_admin(user= None):
    if user is None or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    return user


def get_storage():
    return tasks
