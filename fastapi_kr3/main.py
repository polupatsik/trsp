import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from passlib.context import CryptContext
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from database import get_db_connection, init_db

# ---------------------------------------------------------------------------
# Environment / config
# ---------------------------------------------------------------------------
MODE = os.getenv("MODE", "DEV").upper()
if MODE not in ("DEV", "PROD"):
    raise RuntimeError(f"Invalid MODE value: '{MODE}'. Must be DEV or PROD.")

DOCS_USER = os.getenv("DOCS_USER", "admin")
DOCS_PASSWORD = os.getenv("DOCS_PASSWORD", "secret")

JWT_SECRET = os.getenv("JWT_SECRET", "supersecretkey_change_in_prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 30

# ---------------------------------------------------------------------------
# FastAPI app (docs disabled by default; we add custom routes below)
# ---------------------------------------------------------------------------
app = FastAPI(
    title="KR3 FastAPI",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# ---------------------------------------------------------------------------
# Rate limiter (Task 6.5)
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# Password hashing (Tasks 6.2, 6.5)
# ---------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------------------------------------------------------------------------
# In-memory "DB" for Tasks 6.1–7.1
# ---------------------------------------------------------------------------
# { username: UserInDB }
fake_users_db: dict = {}

# ---------------------------------------------------------------------------
# Pydantic models (Task 6.2)
# ---------------------------------------------------------------------------

class UserBase(BaseModel):
    username: str


class User(UserBase):
    password: str


class UserInDB(UserBase):
    hashed_password: str


# RBAC model (Task 7.1)
class UserInDBWithRole(UserBase):
    hashed_password: str
    role: str  # admin | user | guest


# JWT login payload (Task 6.4 / 6.5)
class LoginPayload(BaseModel):
    username: str
    password: str


# ---------------------------------------------------------------------------
# RBAC definitions (Task 7.1)
# ---------------------------------------------------------------------------
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "admin": ["create", "read", "update", "delete"],
    "user":  ["read", "update"],
    "guest": ["read"],
}

# In-memory store for RBAC users
rbac_users_db: dict[str, UserInDBWithRole] = {}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def create_jwt(data: dict, expires_delta: timedelta | None = None) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=JWT_EXPIRE_MINUTES))
    payload.update({"exp": expire})
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ---------------------------------------------------------------------------
# Task 6.1 – Basic auth /login (GET)
# ---------------------------------------------------------------------------
security = HTTPBasic()

BASIC_USER = os.getenv("BASIC_USER", "admin")
BASIC_PASS = os.getenv("BASIC_PASS", "password")


def verify_basic_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username.encode(), BASIC_USER.encode())
    correct_password = secrets.compare_digest(credentials.password.encode(), BASIC_PASS.encode())
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.get("/login", tags=["6.1 Basic Auth"])
def login_basic(username: str = Depends(verify_basic_credentials)):
    return {"message": "You got my secret, welcome"}


# ---------------------------------------------------------------------------
# Task 6.2 – Secure auth with bcrypt + in-memory DB
# ---------------------------------------------------------------------------

def auth_user(credentials: HTTPBasicCredentials = Depends(security)) -> UserInDB:
    """Dependency: authenticate against fake_users_db using bcrypt."""
    # timing-safe username lookup
    found_user: Optional[UserInDB] = None
    for db_username, db_user in fake_users_db.items():
        if secrets.compare_digest(credentials.username.lower(), db_username.lower()):
            found_user = db_user
            break

    invalid_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Basic"},
    )

    if found_user is None:
        raise invalid_exc
    if not verify_password(credentials.password, found_user.hashed_password):
        raise invalid_exc

    return found_user


@app.post("/register", tags=["6.2 Bcrypt Auth"], status_code=201)
def register_user(user: User):
    if user.username in fake_users_db:
        raise HTTPException(status_code=409, detail="User already exists")
    hashed = hash_password(user.password)
    fake_users_db[user.username] = UserInDB(username=user.username, hashed_password=hashed)
    return {"message": f"User '{user.username}' registered successfully"}


@app.get("/login/secure", tags=["6.2 Bcrypt Auth"])
def login_secure(user: UserInDB = Depends(auth_user)):
    return {"message": f"Welcome, {user.username}!"}


# ---------------------------------------------------------------------------
# Task 6.3 – Docs management (DEV/PROD)
# ---------------------------------------------------------------------------

def verify_docs_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    ok_user = secrets.compare_digest(credentials.username, DOCS_USER)
    ok_pass = secrets.compare_digest(credentials.password, DOCS_PASSWORD)
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )


if MODE == "DEV":
    @app.get("/docs", include_in_schema=False)
    def custom_docs(credentials: HTTPBasicCredentials = Depends(security)):
        verify_docs_credentials(credentials)
        return get_swagger_ui_html(openapi_url="/openapi.json", title="API Docs")

    @app.get("/openapi.json", include_in_schema=False)
    def custom_openapi_json(credentials: HTTPBasicCredentials = Depends(security)):
        verify_docs_credentials(credentials)
        return get_openapi(title=app.title, version="1.0.0", routes=app.routes)

elif MODE == "PROD":
    @app.get("/docs", include_in_schema=False)
    def docs_404():
        raise HTTPException(status_code=404)

    @app.get("/openapi.json", include_in_schema=False)
    def openapi_404():
        raise HTTPException(status_code=404)

    @app.get("/redoc", include_in_schema=False)
    def redoc_404():
        raise HTTPException(status_code=404)


# ---------------------------------------------------------------------------
# Task 6.4 – JWT auth
# ---------------------------------------------------------------------------

def authenticate_user_jwt(username: str, password: str) -> bool:
    """Check in fake_users_db; falls back to stub if user not found."""
    if username in fake_users_db:
        return verify_password(password, fake_users_db[username].hashed_password)
    # stub: random for unknown users (as allowed by task description)
    import random
    return random.choice([True, False])


@app.post("/jwt/login", tags=["6.4 JWT"])
def jwt_login(payload: LoginPayload):
    if not authenticate_user_jwt(payload.username, payload.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_jwt({"sub": payload.username})
    return {"access_token": token}


def get_current_user_jwt(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = auth_header.split(" ", 1)[1]
    payload = decode_jwt(token)
    return payload.get("sub", "unknown")


@app.get("/protected_resource", tags=["6.4 JWT"])
def protected_resource(username: str = Depends(get_current_user_jwt)):
    return {"message": "Access granted", "user": username}


# ---------------------------------------------------------------------------
# Task 6.5 – JWT + register + rate limiting
# ---------------------------------------------------------------------------

@app.post("/v2/register", tags=["6.5 JWT + Rate Limit"], status_code=201)
@limiter.limit("1/minute")
def register_v2(request: Request, user: User):
    if user.username in fake_users_db:
        raise HTTPException(status_code=409, detail="User already exists")
    hashed = hash_password(user.password)
    fake_users_db[user.username] = UserInDB(username=user.username, hashed_password=hashed)
    return {"message": "New user created"}


@app.post("/v2/login", tags=["6.5 JWT + Rate Limit"])
@limiter.limit("5/minute")
def login_v2(request: Request, payload: LoginPayload):
    # timing-safe username lookup
    found_user: Optional[UserInDB] = None
    for db_username, db_user in fake_users_db.items():
        if secrets.compare_digest(payload.username, db_username):
            found_user = db_user
            break

    if found_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not verify_password(payload.password, found_user.hashed_password):
        raise HTTPException(status_code=401, detail="Authorization failed")

    token = create_jwt({"sub": found_user.username})
    return {"access_token": token, "token_type": "bearer"}


# ---------------------------------------------------------------------------
# Task 7.1 – RBAC
# ---------------------------------------------------------------------------

def require_permission(permission: str):
    def dependency(request: Request) -> UserInDBWithRole:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing token")
        token = auth_header.split(" ", 1)[1]
        payload = decode_jwt(token)
        username = payload.get("sub", "")

        user = rbac_users_db.get(username)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found in RBAC DB")

        allowed = ROLE_PERMISSIONS.get(user.role, [])
        if permission not in allowed:
            raise HTTPException(status_code=403, detail=f"Role '{user.role}' cannot '{permission}'")
        return user
    return dependency


@app.post("/rbac/register", tags=["7.1 RBAC"], status_code=201)
def rbac_register(user: User, role: str = "guest"):
    if role not in ROLE_PERMISSIONS:
        raise HTTPException(status_code=400, detail=f"Unknown role '{role}'")
    if user.username in rbac_users_db:
        raise HTTPException(status_code=409, detail="User already exists")
    hashed = hash_password(user.password)
    rbac_users_db[user.username] = UserInDBWithRole(
        username=user.username, hashed_password=hashed, role=role
    )
    return {"message": f"User '{user.username}' registered with role '{role}'"}


@app.post("/rbac/login", tags=["7.1 RBAC"])
def rbac_login(payload: LoginPayload):
    user = rbac_users_db.get(payload.username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Authorization failed")
    token = create_jwt({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/rbac/resource", tags=["7.1 RBAC"])
def rbac_resource(user: UserInDBWithRole = Depends(require_permission("read"))):
    return {"message": f"Read access granted to '{user.username}' (role: {user.role})"}


@app.post("/rbac/resource", tags=["7.1 RBAC"])
def rbac_create_resource(user: UserInDBWithRole = Depends(require_permission("create"))):
    return {"message": f"Resource created by '{user.username}' (role: {user.role})"}


@app.put("/rbac/resource", tags=["7.1 RBAC"])
def rbac_update_resource(user: UserInDBWithRole = Depends(require_permission("update"))):
    return {"message": f"Resource updated by '{user.username}' (role: {user.role})"}


@app.delete("/rbac/resource", tags=["7.1 RBAC"])
def rbac_delete_resource(user: UserInDBWithRole = Depends(require_permission("delete"))):
    return {"message": f"Resource deleted by '{user.username}' (role: {user.role})"}


# ---------------------------------------------------------------------------
# Task 8.1 – SQLite /register
# ---------------------------------------------------------------------------

class UserSQLite(BaseModel):
    username: str
    password: str


@app.on_event("startup")
def startup():
    init_db()


@app.post("/sqlite/register", tags=["8.1 SQLite"], status_code=201)
def sqlite_register(user: UserSQLite):
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (user.username, user.password),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Username already taken")
    finally:
        conn.close()
    return {"message": "User registered successfully!"}


# ---------------------------------------------------------------------------
# Task 8.2 – CRUD Todo with SQLite
# ---------------------------------------------------------------------------

class TodoCreate(BaseModel):
    title: str
    description: str


class TodoUpdate(BaseModel):
    title: str
    description: str
    completed: bool


def todo_row_to_dict(row) -> dict:
    return {
        "id": row[0],
        "title": row[1],
        "description": row[2],
        "completed": bool(row[3]),
    }


@app.post("/todos", tags=["8.2 Todo CRUD"], status_code=201)
def create_todo(todo: TodoCreate):
    conn = get_db_connection()
    try:
        cur = conn.execute(
            "INSERT INTO todos (title, description, completed) VALUES (?, ?, 0)",
            (todo.title, todo.description),
        )
        conn.commit()
        todo_id = cur.lastrowid
        row = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
        return todo_row_to_dict(row)
    finally:
        conn.close()


@app.get("/todos/{todo_id}", tags=["8.2 Todo CRUD"])
def get_todo(todo_id: int):
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Todo not found")
        return todo_row_to_dict(row)
    finally:
        conn.close()


@app.put("/todos/{todo_id}", tags=["8.2 Todo CRUD"])
def update_todo(todo_id: int, todo: TodoUpdate):
    conn = get_db_connection()
    try:
        cur = conn.execute(
            "UPDATE todos SET title=?, description=?, completed=? WHERE id=?",
            (todo.title, todo.description, int(todo.completed), todo_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Todo not found")
        row = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
        return todo_row_to_dict(row)
    finally:
        conn.close()


@app.delete("/todos/{todo_id}", tags=["8.2 Todo CRUD"])
def delete_todo(todo_id: int):
    conn = get_db_connection()
    try:
        cur = conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Todo not found")
        return {"message": f"Todo {todo_id} deleted successfully"}
    finally:
        conn.close()
