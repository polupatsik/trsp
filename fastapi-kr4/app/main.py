from fastapi import FastAPI, HTTPException, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, conint, constr
from typing import Optional
from itertools import count
from threading import Lock

app = FastAPI()

db: dict[int, dict] = {}
_id_seq = count(start=1)
_id_lock = Lock()


def next_user_id() -> int:
    with _id_lock:
        return next(_id_seq)


class User(BaseModel):
    username: str
    age: conint(gt=18)
    email: EmailStr
    password: constr(min_length=8, max_length=16)
    phone: Optional[str] = "Unknown"


class UserIn(BaseModel):
    username: str
    age: int


class UserOut(BaseModel):
    id: int
    username: str
    age: int


class CustomExceptionA(Exception):
    def __init__(self, detail: str):
        self.detail = detail


class CustomExceptionB(Exception):
    def __init__(self, detail: str):
        self.detail = detail


@app.exception_handler(CustomExceptionA)
async def custom_exception_a_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": exc.detail}
    )


@app.exception_handler(CustomExceptionB)
async def custom_exception_b_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": exc.detail}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "message": "Validation error",
            "errors": exc.errors()
        }
    )


@app.get("/")
def root():
    return {"message": "FastAPI KR4 working"}


@app.get("/error-a")
def error_a():
    raise CustomExceptionA("Custom error A")


@app.get("/error-b")
def error_b():
    raise CustomExceptionB("Resource not found")


@app.post("/validate")
def validate_user(user: User):
    return {
        "message": "User validated",
        "user": user.model_dump()
    }


@app.post("/users", response_model=UserOut, status_code=201)
def create_user(user: UserIn):
    user_id = next_user_id()
    db[user_id] = user.model_dump()
    return {"id": user_id, **db[user_id]}


@app.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int):
    if user_id not in db:
        raise HTTPException(status_code=404, detail="User not found")

    return {"id": user_id, **db[user_id]}


@app.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int):
    if db.pop(user_id, None) is None:
        raise HTTPException(status_code=404, detail="User not found")

    return Response(status_code=204)
