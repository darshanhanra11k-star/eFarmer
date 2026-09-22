eFarmer

eFarmer is a digital platform for agricultural procurement.

This repository contains the backend developed so far for the eFarmer project. Other parts of the project, including the frontend, may be maintained separately.

What is included

The backend currently covers:

Farmer and procurement centre data

Eligibility and procurement rules

Centre capacity

Procurement intents

Priority-based centre selection

Daily queues and tokens

Capacity allocation

JWT authentication and role-based access control

PostgreSQL database migrations

OpenAPI documentation

Tech stack

Python 3.13 · FastAPI · Pydantic · SQLAlchemy 2 · PostgreSQL · Alembic · JWT · Pytest · Ruff · Mypy · Docker Compose

Quick start

Windows

Run the first block:

git clone https://github.com/darshanhanra11k-star/eFarmer.git
cd eFarmer
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env

Now open .env and set your own DATABASE_URL and JWT_SECRET_KEY.

Then continue:

docker compose up -d
alembic upgrade head
uvicorn app.main:app --reload --port 8000

Linux / macOS

Run the first block:

git clone https://github.com/darshanhanra11k-star/eFarmer.git
cd eFarmer
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env

Now open .env and set your own DATABASE_URL and JWT_SECRET_KEY.

Then continue:

docker compose up -d
alembic upgrade head
uvicorn app.main:app --reload --port 8000

Database

The included Docker Compose setup is for local development.

Current local PostgreSQL settings:

Host: localhost
Port: 5432
User: postgres
Password: postgres
Database: farmer

Use:

DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/farmer

Use your own database and credentials when using a managed PostgreSQL service.

Do not commit .env.

API

Backend URL:

http://localhost:8000

Swagger:

http://localhost:8000/docs

ReDoc:

http://localhost:8000/redoc

OpenAPI:

http://localhost:8000/openapi.json

The full API reference is in api-contracts.md.

To regenerate it:

python scripts/generate_api_contracts.py

Main endpoints

Area

Method

Endpoint

Health

GET

/api/v1/health

Readiness

GET

/api/v1/ready

Farmers

POST

/api/v1/farmers

Farmers

GET

/api/v1/farmers/{id}

Centres

GET

/api/v1/centres

Capacity

GET

/api/v1/centres/{id}/capacity

Centre selection

POST

/api/v1/farmers/me/centre-selection

Procurement

POST

/api/v1/procurement

Queue

POST

/api/v1/queues/{id}/join

Queue

POST

/api/v1/queues/{id}/call-next

Token

POST

/api/v1/tokens/{id}/process

Token

POST

/api/v1/tokens/{id}/complete

Allocation

GET

/api/v1/centres/{centre_id}/allocation

See api-contracts.md for the complete route list, request bodies, responses and status codes.

Authentication

The API uses Bearer JWT authentication.

There is currently no public login endpoint in this repository. Authentication is handled through the existing JWT flow.

For local development, the repository includes a token helper.

First, find a real user in the local database:

docker compose exec db psql -U postgres -d farmer -c "SELECT id, role FROM users LIMIT 5;"

Use one of the returned id values as USER_ID.

Farmer:

python -c "from app.core.security import create_access_token; from app.core.rbac import Role; print(create_access_token('USER_ID', role=Role.FARMER))"

Officer:

python -c "from app.core.security import create_access_token; from app.core.rbac import Role; print(create_access_token('USER_ID', role=Role.OFFICER))"

USER_ID should be the UUID of an existing user in your local database.

Send the token with:

Authorization: Bearer <token>

Current roles:

FARMER
OFFICER

CORS

Development origins are configured through:

CORS_ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:5173"]

Add the frontend origin to .env when needed.

Do not use a wildcard origin with credentials enabled.

Errors

API errors use a common JSON format:

{
  "code": "error_code",
  "message": "Message",
  "status_code": 400,
  "details": {}
}

Validation errors use the same format with:

{
  "code": "validation_error",
  "message": "Enter a valid value.",
  "status_code": 422,
  "details": {
    "errors": []
  }
}

Database migrations

Apply migrations:

alembic upgrade head

Check the current revision:

alembic current

The current migration head is:

0007

Check whether model changes are missing migrations:

alembic check

alembic check checks for pending model changes that are not represented by migrations. It does not apply migrations.

Tests

Run the full test suite:

pytest -q

Expected:360+ tests passing with 0 failures

Run a specific test file:

pytest tests/test_cors.py
pytest tests/test_priority_centre_api.py

Code checks

ruff check .
ruff format --check .
mypy app tests
alembic check

Project structure

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

Working with the team

Before changing an existing endpoint, check api-contracts.md and the OpenAPI schema.

Keep changes consistent across:

API
Schema
Service
Repository
Model
Tests

Do not add new routes or database changes without checking the existing project structure and team ownership.

Current status

This repository contains the current backend implementation for eFarmer and is ready for frontend integration.

The complete eFarmer project is larger than this repository. Offline sync, ML-based wait-time prediction, payments and external government integrations are not part of this backend release.

Common problems

pydantic_core.ValidationError: JWT_SECRET_KEY

Set JWT_SECRET_KEY in .env. It must meet the minimum length required by the backend.

psycopg.OperationalError: connection refused

PostgreSQL is not running. Start it with:

docker compose up -d

Then check:

docker compose ps

ModuleNotFoundError: No module named 'app'

Install the project:

pip install -e ".[dev]"

Run commands from the repository root.

401 Unauthorized

Check that:

the Authorization header contains a Bearer token

the token has not expired

the server and token generator use the same JWT_SECRET_KEY

Also make sure USER_ID belongs to a user in the local database.

CORS error in the browser

Make sure the frontend origin is listed in CORS_ALLOWED_ORIGINS in .env, then restart the backend.

License

Add a project license when the team decides on one.
