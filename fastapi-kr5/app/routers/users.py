from fastapi import APIRouter, Depends
from app.dependencies import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
def me(user=Depends(get_current_user)):
    return user


@router.get("/{user_id}")
def get_user(user_id: int):
    return {"id": user_id}
