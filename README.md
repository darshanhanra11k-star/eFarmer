# eFarmer

### Agricultural Procurement Backend

FastAPI backend for farmer data, procurement rules, centre capacity, priority-based centre selection, daily queues, tokens, and allocation.

[![Python 3.13](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/Tests-350%2B-2ea44f?style=flat-square)](#tests)

This repository contains the **backend developed so far** for the eFarmer project. Other parts of the project, including the frontend, may be maintained separately.

---

## 1. Scope

Current backend coverage:

| Area | Coverage |
|---|---|
| Farmer data | Registration and retrieval |
| Centre data | Procurement centre information |
| Rules | Eligibility and procurement rules |
| Capacity | Centre capacity checks |
| Procurement | Procurement intents |
| Centre selection | Priority-based selection |
| Queue | Daily queues and tokens |
| Allocation | Capacity allocation |
| Auth | JWT and role-based access control |
| Database | PostgreSQL and Alembic |
| API | FastAPI with OpenAPI documentation |

---

## 2. Stack

| Layer | Technology |
|---|---|
| Language | Python 3.13 |
| API | FastAPI |
| Schemas | Pydantic |
| ORM | SQLAlchemy 2 |
| Database | PostgreSQL |
| Migrations | Alembic |
| Auth | JWT |
| Tests | Pytest |
| Lint | Ruff |
| Types | Mypy |
| Local DB | Docker Compose |

---

## 3. Quick Start

### Windows

**Clone and install**

```powershell
git clone https://github.com/darshanhanra11k-star/eFarmer.git
cd eFarmer
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
```

**Configure `.env`**

Set:

```text
DATABASE_URL=...
JWT_SECRET_KEY=...
```

**Start**

```powershell
docker compose up -d
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Linux / macOS

**Clone and install**

```bash
git clone https://github.com/darshanhanra11k-star/eFarmer.git
cd eFarmer
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

**Configure `.env`**

Set:

```text
DATABASE_URL=...
JWT_SECRET_KEY=...
```

**Start**

```bash
docker compose up -d
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

---

## 4. Database

The included Docker Compose setup is for local development.

### Local PostgreSQL

| Setting | Value |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| User | `postgres` |
| Password | `postgres` |
| Database | `farmer` |

Connection string:

```text
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/farmer
```

For a managed PostgreSQL service, use its own connection details.

Do not commit `.env`.

---

## 5. API

Base URL:

```text
http://localhost:8000
```

### Documentation

| Resource | URL |
|---|---|
| Swagger UI | `http://localhost:8000/docs` |
| ReDoc | `http://localhost:8000/redoc` |
| OpenAPI | `http://localhost:8000/openapi.json` |

FastAPI generates the OpenAPI schema and the Swagger/ReDoc documentation automatically.

The complete API reference is in `api-contracts.md`.

Regenerate it with:

```bash
python scripts/generate_api_contracts.py
```

### Main routes

| Area | Method | Endpoint |
|---|---:|---|
| Health | `GET` | `/api/v1/health` |
| Readiness | `GET` | `/api/v1/ready` |
| Farmers | `POST` | `/api/v1/farmers` |
| Farmers | `GET` | `/api/v1/farmers/{id}` |
| Centres | `GET` | `/api/v1/centres` |
| Capacity | `GET` | `/api/v1/centres/{id}/capacity` |
| Centre selection | `POST` | `/api/v1/farmers/me/centre-selection` |
| Procurement | `POST` | `/api/v1/procurement` |
| Queue | `POST` | `/api/v1/queues/{id}/join` |
| Queue | `POST` | `/api/v1/queues/{id}/call-next` |
| Token | `POST` | `/api/v1/tokens/{id}/process` |
| Token | `POST` | `/api/v1/tokens/{id}/complete` |
| Allocation | `GET` | `/api/v1/centres/{centre_id}/allocation` |

See `api-contracts.md` for the complete route list, request bodies, responses, and status codes.

---

## 6. Authentication

The API uses Bearer JWT authentication.

There is currently no public login endpoint in this repository. Authentication is handled through the existing JWT flow.

### Find a user

```bash
docker compose exec db psql -U postgres -d farmer -c "SELECT id, role FROM users LIMIT 5;"
```

Use one returned ID as `USER_ID`.

### Farmer token

```bash
python -c "from app.core.security import create_access_token; from app.core.rbac import Role; print(create_access_token('USER_ID', role=Role.FARMER))"
```

### Officer token

```bash
python -c "from app.core.security import create_access_token; from app.core.rbac import Role; print(create_access_token('USER_ID', role=Role.OFFICER))"
```

Send:

```text
Authorization: Bearer <token>
```

### Roles

```text
FARMER
OFFICER
```

---

## 7. CORS

Development origins are configured through:

```text
CORS_ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

Add the frontend origin to `.env` when needed.

Do not use a wildcard origin with credentials enabled.

---

## 8. Errors

API errors use a common response format:

```json
{
  "code": "error_code",
  "message": "Message",
  "status_code": 400,
  "details": {}
}
```

Validation errors use the same format:

```json
{
  "code": "validation_error",
  "message": "Enter a valid value.",
  "status_code": 422,
  "details": {
    "errors": []
  }
}
```

---

## 9. Migrations

Apply migrations:

```bash
alembic upgrade head
```

Check the current revision:

```bash
alembic current
```

Current migration head:

```text
0007
```

Check for model changes not represented by migrations:

```bash
alembic check
```

`alembic check` does not apply migrations.

---

## 10. Tests

Run the full suite:

```bash
pytest -q
```

Expected:

```text
350+ tests passing with 0 failures
```

Run selected tests:

```bash
pytest tests/test_cors.py
pytest tests/test_priority_centre_api.py
```

### Code checks

```bash
ruff check .
ruff format --check .
mypy app tests
alembic check
```

---

## 11. Project Structure

```text
eFarmer/
├── .env.example
├── .gitignore
├── alembic.ini
├── app/
│   ├── api/            # API routes
│   ├── allocation/     # Allocation logic
│   ├── capacity/       # Capacity logic
│   ├── core/           # Config, security, RBAC, errors and retry
│   ├── db/             # Database setup
│   ├── models/         # SQLAlchemy models
│   ├── repositories/   # Database queries
│   ├── rules/          # Eligibility rules
│   ├── schemas/        # Request and response schemas
│   └── services/       # Application logic
├── migrations/         # Alembic migrations
├── scripts/            # Project utility scripts
├── docs/               # Project documentation
├── tests/              # Tests
├── api-contracts.md    # API reference
├── docker-compose.yml  # Local PostgreSQL
├── README.md
└── pyproject.toml
```

---

## 12. Team Integration

Before changing an existing endpoint, check:

```text
api-contracts.md
OpenAPI schema
```

Keep changes aligned across:

```text
API
Schema
Service
Repository
Model
Tests
```

Do not add new routes or database changes without checking the existing project structure and team ownership.

---

## 13. Current Status

This repository contains the current backend implementation for eFarmer and is ready for frontend integration.

The complete eFarmer project is larger than this repository. Offline sync, ML-based wait-time prediction, payments, and external government integrations are not part of this backend release.

---

## 14. Common Problems

### `pydantic_core.ValidationError: JWT_SECRET_KEY`

Set `JWT_SECRET_KEY` in `.env`. It must meet the minimum length required by the backend.

### `psycopg.OperationalError: connection refused`

PostgreSQL is not running.

```bash
docker compose up -d
docker compose ps
```

### `ModuleNotFoundError: No module named 'app'`

Install the project:

```bash
pip install -e ".[dev]"
```

Run commands from the repository root.

### `401 Unauthorized`

Check:

- `Authorization` contains a Bearer token
- the token has not expired
- the server and token generator use the same `JWT_SECRET_KEY`
- `USER_ID` belongs to a user in the local database

### CORS error

Check that the frontend origin is listed in `CORS_ALLOWED_ORIGINS` in `.env`, then restart the backend.

---

## License

Add a project license when the team decides on one.
