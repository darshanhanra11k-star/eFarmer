# eFarmer Backend

Backend service for **eFarmer**, an agricultural procurement and queue management platform designed to support farmers, procurement centres, and administrators.

The backend provides the APIs, business rules, slot allocation, queue management, centre capacity handling, authentication, database operations, and reporting services required by the eFarmer platform.

> **Backend Status:** Ready for frontend integration.

---

## Overview

eFarmer helps farmers book procurement slots, track their queue status, and receive updates while allowing procurement centre staff and administrators to manage capacity, queues, procurement records, and system operations.

The system is designed with **low-connectivity areas** in mind. The frontend can continue working with locally stored data and synchronize with the backend when connectivity is available.

This repository contains the **backend implementation and supporting services** for the platform.

---

## Core Features

### Authentication and Access Control

- User login and session handling
- **JWT-based authentication**
- Role-based access for:
  - Farmer
  - Centre Staff
  - Administrator
- Protected API routes
- User and centre access validation

### Farmer and Centre Management

- Farmer profile management
- Farmer eligibility checks
- Procurement centre management
- Centre capacity management
- Centre status and configuration
- Slot availability handling

### Priority-Based Slot Allocation

Farmers can select multiple preferred procurement centres in priority order.

The allocation logic:

1. Farmer selects preferred centres.
2. The system checks the centres in the selected order.
3. Each centre is checked for available capacity and slots.
4. If the first centre is full, the system checks the next centre.
5. The first available slot is assigned.
6. A booking/token is generated for the farmer.

This allows a farmer to provide multiple centre preferences instead of depending on a single centre.

### Queue Management

- Token generation
- Queue position tracking
- Farmers ahead calculation
- Service progress tracking
- Queue status updates
- Queue cancellation and rescheduling
- Centre-wise queue records

### Wait-Time Estimation

The backend maintains the data required for queue wait-time estimation, including:

- Current queue size
- Farmers ahead
- Centre capacity
- Previous processing history
- Current service progress
- Estimated service time

The estimated waiting time can be updated as the queue progresses.

### Procurement Management

- Farmer verification
- Procurement record creation
- Quantity recording
- Procurement completion tracking
- Centre-side procurement updates
- Procurement history

### Payment Records

The backend supports payment-related records and transaction status tracking where payment integration is enabled.

Typical payment states include:

- Initiated
- Verified
- Confirmed

External payment gateway or government payment integration can be connected through the corresponding service layer.

### Monitoring and Reporting

- Queue status
- Procurement data
- Payment status
- Centre-level information
- System logs
- Audit records
- Operational reports

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | **FastAPI** |
| Language | **Python** |
| Database | **PostgreSQL** |
| ORM | **SQLAlchemy** |
| Data Validation | **Pydantic** |
| Authentication | **JWT** |
| Database Migrations | **Alembic** |
| Testing | **Pytest** |
| Code Quality | **Ruff** |
| Type Checking | **Mypy** |
| Local Services | **Docker Compose** |

---

## Architecture

The backend follows a modular structure so that API routes, business rules, database models, and application services remain separated.

```text
                    ┌──────────────────────┐
                    │      Farmer PWA      │
                    └──────────┬───────────┘
                               │
                               │ REST API
                               ▼
                    ┌──────────────────────┐
                    │      FastAPI         │
                    │     API Layer        │
                    └──────────┬───────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
             ▼                 ▼                 ▼
      ┌─────────────┐   ┌──────────────┐  ┌──────────────┐
      │ Allocation  │   │ Queue        │  │ Capacity     │
      │ Logic       │   │ Management   │  │ Management   │
      └──────┬──────┘   └──────┬───────┘  └──────┬───────┘
             │                 │                 │
             └─────────────────┼─────────────────┘
                               ▼
                    ┌──────────────────────┐
                    │    Service Layer     │
                    │ Business Operations  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │     SQLAlchemy       │
                    │         ORM          │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │     PostgreSQL       │
                    └──────────────────────┘
```

---

## Project Structure

```text
eFarmer/
│
├── app/
│   ├── api/
│   │   └── API routes and endpoints
│   │
│   ├── allocation/
│   │   └── Priority-based slot allocation logic
│   │
│   ├── capacity/
│   │   └── Procurement centre capacity logic
│   │
│   ├── core/
│   │   └── Configuration, security, errors and shared utilities
│   │
│   ├── db/
│   │   └── Database configuration and setup
│   │
│   ├── models/
│   │   └── SQLAlchemy database models
│   │
│   ├── rules/
│   │   └── Eligibility and business rules
│   │
│   ├── schemas/
│   │   └── Pydantic request and response schemas
│   │
│   └── services/
│       └── Application and business services
│
├── docs/
│   └── Project documentation
│
├── migrations/
│   └── Alembic database migrations
│
├── scripts/
│   └── Utility and setup scripts
│
├── tests/
│   └── Automated test suite
│
├── .env.example
├── .gitignore
├── alembic.ini
├── api-contracts.md
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

## API Design

The backend exposes REST APIs through FastAPI.

The API contracts are maintained separately in:

**`api-contracts.md`**

Before modifying an existing endpoint, check:

- API contract
- OpenAPI schema
- Request schema
- Response schema
- Service implementation
- Database model
- Existing tests

This keeps the frontend and backend implementations synchronized.

---

## Main Backend Modules

### API Layer

Responsible for:

- HTTP routes
- Request handling
- Response formatting
- Authentication dependencies
- Input validation
- API error handling

### Allocation Module

Responsible for:

- Reading farmer centre preferences
- Checking centre capacity
- Checking slot availability
- Applying priority order
- Assigning the first available centre and slot
- Creating booking records

### Capacity Module

Responsible for:

- Centre capacity
- Available slots
- Capacity checks
- Slot availability
- Capacity updates after allocation or processing

### Rules Module

Responsible for business rules such as:

- Farmer eligibility
- Centre-level constraints
- Booking conditions
- Procurement rules

### Services Layer

Contains application-level operations shared across API routes and other backend components.

---

## Database

The backend uses **PostgreSQL** as the main database.

The database stores information related to:

- Farmers
- Centres
- Centre capacity
- Slots
- Queue records
- Procurement records
- Payment records
- User access
- Audit logs
- System configuration

**SQLAlchemy** is used for database access and **Alembic** is used for schema migrations.

---

## Environment Setup

Create a local environment file from the example configuration:

```bash
cp .env.example .env
```

Configure the required environment variables in `.env`.

Example:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/efarmer
SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
```

Do not commit real credentials or secret keys to GitHub.

---

## Running with Docker

The repository includes a `docker-compose.yml` file for local development.

Start the required services:

```bash
docker compose up -d
```

Check running containers:

```bash
docker compose ps
```

Stop the services:

```bash
docker compose down
```

---

## Running the Backend Locally

Install the project dependencies and start the FastAPI application.

Example:

```bash
uvicorn app.main:app --reload
```

The development server will be available at:

```text
http://127.0.0.1:8000
```

FastAPI documentation is available at:

```text
http://127.0.0.1:8000/docs
```

Alternative OpenAPI documentation:

```text
http://127.0.0.1:8000/redoc
```

---

## Database Migrations

Create a new migration:

```bash
alembic revision --autogenerate -m "describe change"
```

Apply migrations:

```bash
alembic upgrade head
```

Check for model changes that are not represented by migrations:

```bash
alembic check
```

The migration files should always remain consistent with the SQLAlchemy models.

---

## Testing

Run the complete test suite:

```bash
pytest -q
```

Run a specific test file:

```bash
pytest tests/test_core.py
```

or:

```bash
pytest tests/test_priority_centre_api.py
```

The repository includes tests for API behaviour, business rules, allocation logic, and other backend components.

---

## Code Quality

Run Ruff checks:

```bash
ruff check .
```

Format-check the project:

```bash
ruff format --check .
```

Run Mypy:

```bash
mypy app tests
```

Before submitting a change, make sure the affected tests and code-quality checks pass.

---

## Offline-First Integration

The complete eFarmer platform is designed around an **offline-first PWA**.

The frontend can:

- Store required data locally
- Accept supported actions without an active connection
- Queue changes for synchronization
- Reconnect when the network is available
- Send pending changes to the backend
- Receive the latest server state

The backend acts as the server-side source of truth when synchronization occurs.

The sync process must handle:

- Validation
- Duplicate requests
- Conflicting updates
- Server-side business rules
- Updated capacity
- Updated queue state

---

## Team Development

Before changing an existing endpoint, check:

**`api-contracts.md`**

and the current **OpenAPI schema**.

Keep changes consistent across:

- **API**
- **Schema**
- **Service**
- **Repository**
- **Model**
- **Tests**

Do not add a new route or database change without first checking the existing project structure and ownership of that module.

---

## Development Guidelines

### Keep Business Logic Out of Routes

API routes should mainly handle:

- Request validation
- Authentication
- Calling the required service
- Returning the response

Business decisions should remain inside the appropriate service or module.

### Keep Database Access Centralized

Use the existing database and repository/service structure rather than creating separate direct database access inside API routes.

### Validate Important Operations

Operations such as slot booking, queue updates, capacity changes, and procurement updates should be validated on the backend even when the frontend already performs validation.

The backend must remain the final validation layer.

---

## Current Backend Scope

This repository contains the current backend implementation for **eFarmer** and is structured for frontend integration.

The larger eFarmer platform may contain additional components outside this repository.

The following areas are **not part of this backend release**:

- Offline storage implementation in the PWA
- Frontend UI
- ML-based wait-time prediction model
- Final external payment integration
- External government service integrations

These components can be connected through the defined API and service interfaces as the complete system is developed.

---

## Project Status

### Implemented

- FastAPI backend structure
- PostgreSQL database integration
- SQLAlchemy models
- Alembic migrations
- JWT authentication
- Role-based access
- Farmer and centre management
- Capacity management
- Priority-based allocation logic
- Queue management
- API contracts
- Automated tests
- Code-quality checks

### Integration Ready

- Farmer PWA
- Centre staff interface
- Admin portal
- Offline synchronization layer
- Notification services
- External payment services
- Additional prediction and analytics components

---

## Repository Files

| File | Purpose |
|---|---|
| `README.md` | Project documentation |
| `api-contracts.md` | API contract reference |
| `pyproject.toml` | Python project configuration |
| `alembic.ini` | Alembic configuration |
| `docker-compose.yml` | Local service configuration |
| `.env.example` | Environment variable template |

---

## Security

Do not commit:

- API keys
- Database passwords
- JWT secrets
- Private credentials
- Production environment files

Use `.env` for local configuration and keep `.env` excluded from version control.

---

## Backend Flow

A typical farmer booking flow is:

```text
Farmer
   │
   ▼
PWA
   │
   ▼
Login / Authentication
   │
   ▼
Select Preferred Centres
   │
   ▼
Priority-Based Allocation
   │
   ├── Centre 1 → Capacity Available → Assign Slot
   │
   ├── Centre 1 → Full
   │        ↓
   │      Check Centre 2
   │
   ├── Centre 2 → Full
   │        ↓
   │      Check Centre 3
   │
   └── Available Centre → Create Booking
                              │
                              ▼
                         Queue Entry
                              │
                              ▼
                         Status Updates
```

This sequence keeps the allocation decision on the backend so that centre capacity and booking conflicts are validated centrally.

---

## License

This project is developed as part of the **Smart India Hackathon (SIH)** project for problem statement **SIH26032**.
