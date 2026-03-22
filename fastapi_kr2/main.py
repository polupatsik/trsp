from fastapi import FastAPI, Response, HTTPException, Header, Cookie
from typing import Optional
from models import UserCreate
import uuid
from itsdangerous import Signer, BadSignature
from datetime import datetime

app = FastAPI()

@app.post("/create_user")
def create_user(user: UserCreate):
    return user


sample_products = [
    {"product_id": 123, "name": "Smartphone", "category": "Electronics", "price": 599.99},
    {"product_id": 456, "name": "Phone Case", "category": "Accessories", "price": 19.99},
    {"product_id": 789, "name": "Iphone", "category": "Electronics", "price": 1299.99},
    {"product_id": 101, "name": "Headphones", "category": "Accessories", "price": 99.99},
    {"product_id": 202, "name": "Smartwatch", "category": "Electronics", "price": 299.99},
]

@app.get("/product/{product_id}")
def get_product(product_id: int):
    for product in sample_products:
        if product["product_id"] == product_id:
            return product
    raise HTTPException(status_code=404, detail="Product not found")


@app.get("/products/search")
def search_products(keyword: str, category: Optional[str] = None, limit: int = 10):
    results = []

    for product in sample_products:
        if keyword.lower() in product["name"].lower():
            if category:
                if product["category"] == category:
                    results.append(product)
            else:
                results.append(product)

    return results[:limit]


SECRET_KEY = "supersecretkey"
signer = Signer(SECRET_KEY)

fake_user = {
    "username": "user123",
    "password": "password123"
}

@app.post("/login")
def login(response: Response, username: str, password: str):
    if username == fake_user["username"] and password == fake_user["password"]:
        user_id = str(uuid.uuid4())

        signed_token = signer.sign(user_id.encode()).decode()

        response.set_cookie(
            key="session_token",
            value=signed_token,
            httponly=True,
            max_age=300
        )

        return {"message": "Logged in"}

    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/profile")
def profile(session_token: Optional[str] = Cookie(None)):
    if not session_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        user_id = signer.unsign(session_token.encode()).decode()
        return {"user_id": user_id}
    except BadSignature:
        raise HTTPException(status_code=401, detail="Invalid session")


@app.get("/headers")
def get_headers(
    user_agent: str = Header(...),
    accept_language: str = Header(...)
):
    return {
        "User-Agent": user_agent,
        "Accept-Language": accept_language
    }


@app.get("/info")
def info(
    response: Response,
    user_agent: str = Header(...),
    accept_language: str = Header(...)
):
    response.headers["X-Server-Time"] = datetime.utcnow().isoformat()

    return {
        "message": "Добро пожаловать! Ваши заголовки успешно обработаны.",
        "headers": {
            "User-Agent": user_agent,
            "Accept-Language": accept_language
        }
    }