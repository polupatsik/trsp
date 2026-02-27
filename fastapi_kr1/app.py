from fastapi import FastAPI
from fastapi.responses import FileResponse
from models import User, UserWithAge, Feedback

app = FastAPI()


@app.get("/json")
def root_json():
    return {"message": "123"}



@app.get("/")
def get_html():
    return FileResponse("index.html")



@app.post("/calculate")
def calculate(num1: int, num2: int):
    return {"result": num1 + num2}



user_instance = User(
    name="Дружков Михаил",
    id=1
)

@app.get("/users")
def get_user():
    return user_instance



@app.post("/user")
def check_user(user: UserWithAge):
    is_adult = user.age >= 18

    return {
        "name": user.name,
        "age": user.age,
        "is_adult": is_adult
    }



feedbacks = []

@app.post("/feedback")
def create_feedback(feedback: Feedback):
    feedbacks.append(feedback)

    return {
        "message": f"Спасибо, {feedback.name}! Ваш отзыв сохранён."
    }