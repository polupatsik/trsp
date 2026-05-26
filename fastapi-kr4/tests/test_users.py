import pytest
from faker import Faker

fake = Faker()


@pytest.mark.asyncio
async def test_create_user(client):
    payload = {
        "username": fake.user_name(),
        "age": fake.random_int(min=18, max=60)
    }

    response = await client.post("/users", json=payload)

    assert response.status_code == 201

    data = response.json()

    assert data["username"] == payload["username"]
    assert data["age"] == payload["age"]
    assert "id" in data


@pytest.mark.asyncio
async def test_get_existing_user(client):
    payload = {
        "username": fake.user_name(),
        "age": 25
    }

    create_response = await client.post("/users", json=payload)
    user_id = create_response.json()["id"]

    response = await client.get(f"/users/{user_id}")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_nonexistent_user(client):
    response = await client.get("/users/999")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_existing_user(client):
    payload = {
        "username": fake.user_name(),
        "age": 30
    }

    create_response = await client.post("/users", json=payload)
    user_id = create_response.json()["id"]

    response = await client.delete(f"/users/{user_id}")

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_twice(client):
    payload = {
        "username": fake.user_name(),
        "age": 40
    }

    create_response = await client.post("/users", json=payload)
    user_id = create_response.json()["id"]

    await client.delete(f"/users/{user_id}")

    response = await client.delete(f"/users/{user_id}")

    assert response.status_code == 404
