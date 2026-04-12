# KR3 – FastAPI Security & Database

Контрольная работа №3 по дисциплине «Технологии разработки серверных приложений».  
Покрывает задания **6.1 – 6.5, 7.1, 8.1, 8.2**.

---

## Установка и запуск

```bash
# 1. Клонировать репозиторий
git clone <repo-url>
cd fastapi_kr3

# 2. Создать виртуальное окружение
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Создать .env на основе примера
cp .env.example .env        # при необходимости отредактировать

# 5. Запустить приложение
uvicorn main:app --reload
```

Приложение будет доступно по адресу: http://localhost:8000

---

## Переменные окружения

| Переменная    | По умолчанию | Описание                                |
|---------------|--------------|-----------------------------------------|
| MODE          | DEV          | DEV – docs с паролем, PROD – docs 404  |
| DOCS_USER     | admin        | Логин для /docs (DEV)                   |
| DOCS_PASSWORD | secret       | Пароль для /docs (DEV)                  |
| BASIC_USER    | admin        | Логин для GET /login (6.1)              |
| BASIC_PASS    | password     | Пароль для GET /login (6.1)             |
| JWT_SECRET    | change_me... | Секрет для подписи JWT                  |

---

## Тестирование через curl

### Задание 6.1 – Basic Auth /login
```bash
# Успешный вход
curl -u admin:password http://localhost:8000/login

# Неверные данные → 401
curl -u admin:wrong http://localhost:8000/login
```

### Задание 6.2 – Bcrypt + /register + /login/secure
```bash
# Регистрация
curl -X POST -H "Content-Type: application/json" \
  -d '{"username":"user1","password":"correctpass"}' \
  http://localhost:8000/register

# Успешный логин
curl -u user1:correctpass http://localhost:8000/login/secure

# Неверный пароль → 401
curl -u user1:wrongpass http://localhost:8000/login/secure
```

### Задание 6.3 – Docs (DEV/PROD)
```bash
# DEV: открыть /docs с учётными данными
curl -u admin:secret http://localhost:8000/docs

# PROD: /docs возвращает 404
# (установите MODE=PROD в .env и перезапустите)
curl http://localhost:8000/docs
```

### Задание 6.4 – JWT
```bash
# Получить токен (нужно предварительно зарегистрироваться через /register)
TOKEN=$(curl -s -X POST -H "Content-Type: application/json" \
  -d '{"username":"user1","password":"correctpass"}' \
  http://localhost:8000/jwt/login | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Защищённый ресурс
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/protected_resource

# Без токена → 401
curl http://localhost:8000/protected_resource
```

### Задание 6.5 – JWT + Rate Limiter
```bash
# Регистрация (лимит 1 req/min)
curl -X POST -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"qwerty123"}' \
  http://localhost:8000/v2/register

# Логин (лимит 5 req/min)
curl -X POST -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"qwerty123"}' \
  http://localhost:8000/v2/login
```

### Задание 7.1 – RBAC
```bash
# Зарегистрировать admin
curl -X POST -H "Content-Type: application/json" \
  -d '{"username":"boss","password":"adminpass"}' \
  "http://localhost:8000/rbac/register?role=admin"

# Зарегистрировать guest
curl -X POST -H "Content-Type: application/json" \
  -d '{"username":"visitor","password":"guestpass"}' \
  "http://localhost:8000/rbac/register?role=guest"

# Логин, получить токен
ADMIN_TOKEN=$(curl -s -X POST -H "Content-Type: application/json" \
  -d '{"username":"boss","password":"adminpass"}' \
  http://localhost:8000/rbac/login | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# admin может удалять → 200
curl -X DELETE -H "Authorization: Bearer $ADMIN_TOKEN" http://localhost:8000/rbac/resource

GUEST_TOKEN=$(curl -s -X POST -H "Content-Type: application/json" \
  -d '{"username":"visitor","password":"guestpass"}' \
  http://localhost:8000/rbac/login | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# guest не может удалять → 403
curl -X DELETE -H "Authorization: Bearer $GUEST_TOKEN" http://localhost:8000/rbac/resource
```

### Задание 8.1 – SQLite /sqlite/register
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"username":"test_user","password":"12345"}' \
  http://localhost:8000/sqlite/register
```

### Задание 8.2 – Todo CRUD
```bash
# Создать
curl -X POST -H "Content-Type: application/json" \
  -d '{"title":"Buy groceries","description":"Milk, eggs, bread"}' \
  http://localhost:8000/todos

# Получить
curl http://localhost:8000/todos/1

# Обновить
curl -X PUT -H "Content-Type: application/json" \
  -d '{"title":"Buy groceries","description":"Milk, eggs, bread","completed":true}' \
  http://localhost:8000/todos/1

# Удалить
curl -X DELETE http://localhost:8000/todos/1
```

---

## Структура проекта

```
fastapi_kr3/
├── main.py          # Все эндпоинты (задания 6.1–8.2)
├── database.py      # SQLite подключение и init_db()
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```
