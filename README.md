# Farmer Backend

A production-grade, concurrency-safe FastAPI backend for agricultural procurement management, slot and priority centre selection, queue token dispatching, and capacity allocation.

---

## 1. Project

**Farmer Backend** (`farmer-backend`) is the core operational backend service designed for farmer procurement workflows. It manages farmer profiles, procurement centres, crop definitions, daily procurement capacity, queue tokens, procurement intents, persistent capacity allocations, and farmer preferred-centre evaluations.

---

## 2. Purpose

During crop procurement seasons, agricultural centres face high volumes of farmer arrivals and capacity constraints. This backend provides:
- **Fair, Rule-Based Capacity Allocation:** Evaluates incoming procurement intents against centre capacity constraints, prioritising small and marginal farmers with deterministic tie-breaking.
- **Priority Centre Selection:** Allows farmers to submit an ordered list of preferred centres and short-circuits to the first centre with available capacity.
- **Concurrency-Safe Queue Tokens:** Manages token issuing and counter servicing with row-level database locking to prevent race conditions or duplicate calling.
- **Strict Role-Based Access Control:** Enforces resource isolation between farmers and centre officers.

---

## 3. Current Backend Scope

The backend implements the following verified milestones:
- **Phase 9:** Core domain entities (`farmers`, `users`, `procurement_centres`, `crops`, `farmer_land_holdings`, `counters`).
- **Phase 10:** Daily queues, queue entries, and token state machine (`WAITING` $\rightarrow$ `CALLED` $\rightarrow$ `PROCESSING` $\rightarrow$ `COMPLETED` / `CANCELLED`).
- **Phase 11–13:** Multi-factor eligibility and allocation rule engine.
- **Phase 14:** In-memory allocation engine with land holding weighting and deterministic hash tie-breaking.
- **Phase 15:** Concurrency hardening, `SELECT ... FOR UPDATE` row-level locking, serialization retry decorators, and service-owned transaction boundaries.
- **Phase 15.5A:** Persistent allocation runs (`allocation_runs`), persistent allocation decisions (`allocation_decisions`), and automatic capacity status transitions (`AVAILABLE`, `PARTIAL`, `FULL`).
- **Phase 15.5B:** Backend-only Priority Centre Selection service and endpoint (`POST /api/v1/farmers/me/centre-selection`).

---

## 4. Architecture

The system follows a strict **Clean Architecture (Layered Architecture)**:

```
[ HTTP Request ]
       │
       ▼
┌───────────────────────────────────────────────┐
│ Presentation Layer (app/api/v1/)              │
│ - Route endpoints, status codes, OpenAPI docs │
│ - Dependency injection (Auth, DB, Services)   │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│ Business Logic Layer (app/services/)          │
│ - OWNS transaction boundaries                 │
│ - session.commit() / session.rollback()       │
│ - Domain workflows & business rules           │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│ Data Access Layer (app/repositories/)         │
│ - Pure query execution & row locking          │
│ - ZERO session.commit() calls                 │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│ Storage Layer (PostgreSQL)                    │
│ - Schema migrations 0001 through 0007         │
└───────────────────────────────────────────────┘
```

### Key Architectural Invariants:
1. **Transaction Ownership:** Only services own the transaction boundary. Repositories never commit sessions.
2. **Deterministic Locking:** Mutating queue and capacity operations use `SELECT ... FOR UPDATE` to avoid phantom reads and race conditions.
3. **Rollback Safety:** All service mutations catch errors, perform `await session.rollback()`, and raise typed domain exceptions.

---

## 5. Requirements

- **Python:** `3.13` (strictly `>=3.13, <3.14`)
- **Database:** `PostgreSQL 15+` (local container or managed instance)
- **Container Runtime (optional):** Docker & Docker Compose for local database execution

---

## 6. Clone

```bash
git clone <repository-url>
cd farmer
```

---

## 7. Virtual Environment

### Linux / macOS:
```bash
python3.13 -m venv .venv
source .venv/bin/activate
```

### Windows (PowerShell):
```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
```

---

## 8. Dependency Installation

Install all runtime dependencies and development tools in editable mode:

```bash
pip install -e ".[dev]"
```

Verify installed packages:
```bash
pip list
```

---

## 9. Environment Configuration

Create a local `.env` configuration file from the template:

### Linux / macOS:
```bash
cp .env.example .env
```

### Windows (PowerShell):
```powershell
Copy-Item .env.example .env
```

### Configuration Variables in `.env`:

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `APP_NAME` | string | `"Farmer Backend"` | Application display name |
| `ENVIRONMENT` | string | `"development"` | Environment (`development`, `staging`, `production`) |
| `DATABASE_URL` | string | *Required* | Async connection URL (`postgresql+psycopg://...`) |
| `DB_POOL_SIZE` | integer | `10` | SQLAlchemy connection pool size (1–100) |
| `DB_MAX_OVERFLOW` | integer | `20` | Max overflow pool connections (0–100) |
| `DB_POOL_TIMEOUT` | integer | `30` | Seconds to wait before timing out on pool checkout |
| `DB_POOL_RECYCLE` | integer | `1800` | Seconds after which connections are recycled |
| `DB_SQL_ECHO` | boolean | `false` | Enable SQL query echo logging |
| `JWT_SECRET_KEY` | string | *Required* | Minimum 32-character secret key for JWT signing |
| `JWT_ALGORITHM` | string | `"HS256"` | JWT algorithm (`HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | integer | `30` | Access token lifespan in minutes (1–1440) |
| `CORS_ALLOWED_ORIGINS` | JSON list | `["http://localhost:3000", "http://localhost:5173"]` | Allowed CORS origins |

> [!IMPORTANT]
> The database connection URL **must** use the `postgresql+psycopg://` scheme for SQLAlchemy 2.0 async compatibility.

---

## 10. PostgreSQL Setup

You can run PostgreSQL locally using Docker or connect to an external database.

### Option A: Local PostgreSQL via Docker Compose (Recommended)

Start an isolated PostgreSQL 16 container:
```bash
docker compose up -d
```

Verify the container is healthy:
```bash
docker compose ps
```

The service runs on `localhost:5432` with database `farmer`, user `user`, and password `password`. The default `DATABASE_URL` in `.env.example` points directly to this service:
```
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/farmer
```

### Option B: External / Supabase Database
If using Supabase or another managed provider, configure the `DATABASE_URL` in `.env` using your provider credentials and port (typically `5432` or pooler port `6543`).

---

## 11. Migration Setup

Apply all database migrations up to the current head (`0007`):

```bash
alembic upgrade head
```

Verify migration status:
```bash
alembic current
```
Output should display `0007 (head)`.

### Migration Lineage Overview:
- `0001_phase9_farmer_centre.py`: Users, farmers, centres, produce, land holdings, counters.
- `0002_phase10_queue_token.py`: Daily queues, queue entries, and tokens.
- `0003_remove_queue_entry_status.py`: Removes redundant entry status column.
- `0004_m4_procurement_schema.py`: Procurement intents, tokens, and records.
- `0005_m4_capacity_records.py`: Centre capacity records and quantity constraints.
- `0006_remove_uq_intent_slot.py`: Drops unconditional slot constraint, preserves `uq_active_intent_slot`.
- `0007_allocation_persistence.py`: Persistent `allocation_runs` and `allocation_decisions`.

---

## 12. Start Backend

Run the development server with live reload:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify service health:
- Liveness probe: `curl http://localhost:8000/api/v1/health` $\rightarrow$ `{"status": "ok"}`
- Readiness probe: `curl http://localhost:8000/api/v1/ready` $\rightarrow$ `{"status": "ready"}`

---

## 13. OpenAPI Docs

FastAPI exposes interactive API documentation out of the box:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Raw OpenAPI Schema:** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## 14. API Contract Generation

The repository contains a deterministic API contract generator that inspects the live FastAPI OpenAPI schema and generates the project's root `api-contracts.md`:

```bash
python scripts/generate_api_contracts.py
```

This guarantees that frontend teams always have access to an authoritative, up-to-date markdown reference without needing a running server.

---

## 15. Authentication

Authentication uses stateless **Bearer JWT Tokens**. The incoming `Authorization: Bearer <token>` header is decoded in `app/dependencies/auth.py`.

### Token Payload Structure:
```json
{
  "sub": "<user-or-entity-id>",
  "role": "FARMER",
  "iat": 1726000000,
  "exp": 1726001800
}
```

### Development Token Generation:
There is currently **no public login endpoint** (`/api/v1/auth/login`) in the backend. Tokens are issued upstream or generated locally via the built-in helper:

#### Generate a Farmer Token:
```bash
python -c "from app.core.security import create_access_token; from app.core.rbac import Role; print(create_access_token('test-farmer-id', role=Role.FARMER))"
```

#### Generate an Officer Token:
```bash
python -c "from app.core.security import create_access_token; from app.core.rbac import Role; print(create_access_token('test-officer-id', role=Role.OFFICER))"
```

Use the returned JWT in your HTTP headers:
```
Authorization: Bearer <token>
```

---

## 16. RBAC Roles Actually Implemented

The system implements strictly **two roles** defined in `app/core/rbac.py`:

```python
class Role(StrEnum):
    FARMER = "FARMER"
    OFFICER = "OFFICER"
```

*(Note: There is no `ADMIN` role in the active codebase).*

### Role Permissions:

| Permission | `Role.FARMER` | `Role.OFFICER` |
| :--- | :---: | :---: |
| `farmer:read` | Allowed | Allowed |
| `farmer:write` | Allowed | Allowed |
| `queue:read` | Allowed | Allowed |
| `queue:join` | Allowed | — |
| `queue:manage` | — | Allowed |
| `procurement:read` | Allowed | Allowed |
| `procurement:create` | — | Allowed |

### Resource Isolation Invariants:
- **Farmer Isolation:** Farmers can only access their own intents, tokens, and allocations (`farmer_id == current_user.subject`).
- **Officer Isolation:** Centre officers can only manage tokens, queues, and capacities for the centre assigned to their profile.

---

## 17. Frontend Integration

| Question | Answer |
| :--- | :--- |
| **Backend Base URL** | `http://localhost:8000` (configurable in frontend `.env`) |
| **Auth Header** | `Authorization: Bearer <JWT>` on all authenticated endpoints |
| **Public Endpoints** | `GET /api/v1/health`, `GET /api/v1/ready` |
| **Farmer Endpoints** | Priority centre selection, self-intent allocation query, queue join |
| **Officer Endpoints** | Create farmer, call next token, process token, complete token, cancel token |
| **Pagination Format** | Standard envelope: `{"items": [...], "total": int, "page": int, "page_size": int, "total_pages": int}` |

---

## 18. CORS

CORS is managed by `fastapi.middleware.cors.CORSMiddleware` in `app/main.py`.

- **Development Defaults:** `http://localhost:3000` and `http://localhost:5173`.
- **Allowed Methods:** `GET`, `POST`, `PATCH`, `DELETE`, `OPTIONS`.
- **Allowed Headers:** `Authorization`, `Content-Type`.
- **Credentials:** `allow_credentials=True`.

> [!WARNING]
> Wildcard origin (`"*"`) is strictly prohibited when `allow_credentials=True`. Always specify explicit origins in `CORS_ALLOWED_ORIGINS`.

To allow an additional frontend port (e.g. `http://localhost:4000`), update `.env`:
```env
CORS_ALLOWED_ORIGINS=["http://localhost:3000", "http://localhost:5173", "http://localhost:4000"]
```

---

## 19. Error Response Format

All API errors return a standard JSON error envelope:

```json
{
  "code": "string",
  "message": "string",
  "status_code": 400,
  "details": {}
}
```

### Standard Status Codes:
- **`401 Unauthorized` (`code: "unauthenticated"`):** Missing, expired, or malformed JWT token.
- **`403 Forbidden` (`code: "permission_denied"`):** Role mismatch or accessing another user's resources.
- **`404 Not Found` (`code: "not_found"`):** Target resource ID does not exist.
- **`409 Conflict` (`code: "conflict"`):** State transition conflict, duplicate token, or capacity constraint.
- **`422 Unprocessable Entity` (`code: "validation_error"`):** Request body or query parameter validation failure. Details contain `{"errors": [...]}`.
- **`500 Internal Error` (`code: "internal_error"`):** Unexpected server error. Internal stack traces are sanitized.
- **`503 Service Unavailable` (`code: "service_unavailable"`):** Database unreachable (returned by `/api/v1/ready`).

---

## 20. Testing

The project uses `pytest` with `pytest-asyncio`.

Run the full test suite:
```bash
pytest -q
```

Run tests with verbose reporting:
```bash
pytest -v
```

Run a specific test module:
```bash
pytest tests/test_cors.py
pytest tests/test_priority_centre_api.py
```

---

## 21. Ruff (Linting & Formatting)

Check code quality and import formatting:
```bash
ruff check .
```

Verify formatting:
```bash
ruff format --check .
```

Automatically apply formatting fixes:
```bash
ruff format .
```

---

## 22. Mypy (Strict Type Checking)

Execute type analysis in strict mode:
```bash
mypy app tests
```

---

## 23. Project Structure

```
farmer/
├── .env.example                      # Environment configuration template
├── .gitignore                        # Git ignore rules for build/cache artifacts
├── alembic.ini                       # Alembic database migration configuration
├── api-contracts.md                  # Auto-generated API documentation
├── docker-compose.yml                # PostgreSQL container service definition
├── pyproject.toml                    # Package metadata and tool configurations
├── README.md                         # Developer guide and onboarding documentation
├── app/
│   ├── api/                          # HTTP routes and dependency routers
│   │   ├── deps.py                   # Common route dependencies
│   │   ├── router.py                 # Primary v1 API router aggregation
│   │   └── v1/                       # Individual resource routers
│   ├── capacity/                     # Capacity computation engine
│   ├── core/                         # Core configurations, exceptions, RBAC, retry
│   ├── db/                           # SQLAlchemy engine, session factory, base models
│   ├── models/                       # SQLAlchemy ORM declarative models
│   ├── repositories/                 # Data access queries (zero session.commit)
│   ├── rules/                        # Eligibility and allocation business rules
│   ├── schemas/                      # Pydantic validation and response models
│   ├── services/                     # Business services (own transaction boundaries)
│   └── main.py                       # FastAPI application factory and lifespan
├── migrations/
│   ├── env.py                        # Alembic async migration environment
│   └── versions/                     # Revisions 0001 through 0007
├── scripts/
│   ├── 0007_allocation_persistence.sql # Standalone DDL reference for 0007
│   └── generate_api_contracts.py     # Deterministic API contract generator
└── tests/                            # Pytest test suite (360+ tests)
```

---

## 24. Database Ownership

This repository **owns** its schema migrations (`migrations/versions/0001` through `0007`). 

When deploying against a fresh database, run `alembic upgrade head` to establish all tables, constraints, partial unique indexes, and foreign keys. Do not execute raw SQL DDL manually unless running in an environment without Alembic CLI access.

---

## 25. Implemented Modules

- **Farmer Management:** `FarmerService`, `FarmerRepository`, `app/api/v1/farmers.py`.
- **Centre Management:** `CentreService`, `CentreRepository`, `app/api/v1/centres.py`.
- **Capacity Management:** `CapacityService`, `CapacityRepository`, `CapacityEngine`, `app/api/v1/capacity.py`.
- **Queue & Tokens:** `QueueService`, `TokenRepository`, `QueueRepository`, `app/api/v1/queues.py`, `app/api/v1/tokens.py`.
- **Procurement Intents:** `ProcurementService`, `ProcurementRepository`, `app/api/v1/procurement.py`.
- **Allocation Engine:** `AllocationEngine`, `AllocationService`, persistent runs (`AllocationRun`), persistent decisions (`AllocationDecision`).
- **Priority Centre Selection:** `PriorityCentreService`, `POST /api/v1/farmers/me/centre-selection`.

---

## 26. Not-Yet-Implemented Modules & Limitations

- **User Self-Registration / Login:** There is no public user signup or password authentication route (`/api/v1/auth/login`). JWT tokens are generated by an upstream identity provider or using the development helper.
- **Payment Processing:** Payment calculations and disbursement status tracking (`procurement_records.payment_*`) are not part of this core release.
- **Machine Learning Wait-Time Prediction:** Wait-time predictions (`/api/v1/ml/wait-time`) are planned for a subsequent service.
- **Offline Device Sync:** Dedicated conflict-resolution sync endpoints (`/api/v1/sync`) are not implemented in this release.

---

## 27. Common Setup Problems

### Problem 1: `psycopg.InterfaceError: Psycopg cannot use the 'ProactorEventLoop'` on Windows
* **Cause:** Python on Windows uses `ProactorEventLoop` by default, which is incompatible with `psycopg 3` async mode.
* **Resolution:** `app/main.py` automatically sets `asyncio.WindowsSelectorEventLoopPolicy()` when running on `win32`. If running custom scratch scripts outside `app.main`, ensure the loop policy is configured.

### Problem 2: `401 Unauthorized` on All API Calls
* **Cause:** Missing or mismatched `JWT_SECRET_KEY` in `.env`, or expired token.
* **Resolution:** Ensure the `JWT_SECRET_KEY` in your `.env` matches the key used to generate your development token, and verify the token has not expired.

### Problem 3: CORS Blocked in Browser Frontend
* **Cause:** Frontend running on an origin not listed in `CORS_ALLOWED_ORIGINS`.
* **Resolution:** Add your frontend origin (e.g. `"http://localhost:3000"`) to `CORS_ALLOWED_ORIGINS` in `.env` and restart FastAPI.

### Problem 4: `403 Permission Denied` on Officer Routes
* **Cause:** Calling an officer endpoint with a `FARMER` token or operating on a centre ID not assigned to the officer.
* **Resolution:** Generate an officer token with `role=Role.OFFICER` and ensure the officer's centre ID matches the centre in the request.
