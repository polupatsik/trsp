from pydantic import BaseModel, Field, field_validator
import re


class User(BaseModel):
    name: str
    id: int


class UserWithAge(BaseModel):
    name: str
    age: int


class Feedback(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    message: str = Field(..., min_length=10, max_length=500)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str):
        forbidden_words = ["кринж", "рофл", "вайб"]

        value_lower = value.lower()

        for word in forbidden_words:
            if re.search(rf"{word}\w*", value_lower):
                raise ValueError("Использование недопустимых слов")

        return value