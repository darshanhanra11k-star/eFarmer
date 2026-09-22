# EXECUTION BLOCKED — PLAN REQUIRES SCOPE CORRECTION

## 1. Current Verified State

- **Phase 14 — Complete**: Pure `AllocationEngine` implementation with deterministic waiting age and SHA-256 tie-breaking logic.
- **Phase 15 — Complete**: Concurrency safety, service-owned transaction boundaries, zero repository commits, and transient retry support.
- **Phase 15.5A — Complete**: Persistent `allocation_runs` and `allocation_decisions` tables created, migration `0007` applied, live Supabase schema verified, zero repository commits maintained.
- **Current Alembic Head**: `0007` (local and live Supabase aligned).
- **Constraints**: `uq_intent_slot` removed locally and remotely; `uq_active_intent_slot` preserved.
- **Capacity Status Enum**: Exactly `INACTIVE`, `AVAILABLE`, `PARTIAL`, `FULL`.
- **Slot Schema Status**: No authoritative slot/booking table exists locally or remotely. No slot schema will be created in this phase.

---

## 2. Phase 15.5B Objective

- Implement **Priority Centre Selection** as a pure backend evaluation service and API without modifying the database schema.
- Terminology boundary: This phase is strictly **"Priority Centre Selection"**, NOT "Slot Booking".
- Product statement: *"Farmers select multiple centres by priority. The system checks them in order and selects the first centre with sufficient availability."*
- Real slot assignment and slot booking tables remain deferred until an authoritative slot schema contract is finalized.

---

## 3. Priority-Centre Selection Rules

1. The service accepts an ordered sequence of centre preferences with explicit 1-based priorities (`priority 1`, `priority 2`, `priority 3`, ...).
2. The system evaluates centres strictly in ascending priority order (`priority=1` first, followed by `priority=2`, etc.).
3. Centre evaluation stops **immediately** at the first centre that meets all availability criteria.
4. Lower-priority centres are **never evaluated** once an available centre is identified.
5. If no centre satisfies the availability criteria, the system returns a domain-level `"no preferred centre available"` result with diagnostic failure reasons for each evaluated centre.
6. The system never selects centres randomly and never overrides farmer priority with capacity magnitude heuristics.

---

## 4. Availability Definition

For a given centre, crop, target date, and requested quantity, a centre is defined as **available** if and only if all five conditions are met:

1. **Centre Exists**: `ProcurementCentre` record is found by `centre_id`.
2. **Centre is Active**: `centre.active is True`.
3. **Capacity Record Exists**: `CapacityRecord` exists for `(centre_id, crop_id, ready_date)`.
4. **Capacity is Active**: Evaluated via existing Phase 13 `CapacityEngine.calculate(...)`, confirming `metrics.capacity_status != CapacityStatus.INACTIVE`.
5. **Available Capacity is Sufficient**: `metrics.available_capacity_kg >= requested_quantity_kg`.

If any condition is not met, the centre is deemed unavailable, the specific failure reason is recorded, and evaluation moves immediately to the next preferred centre.

---

## 5. Service Design

### Class: `PriorityCentreService` (`app/services/priority_centre.py`)

- **Dependencies**:
  - `centre_repo: CentreRepository` (read-only queries)
  - `capacity_repo: CapacityRepository` (read-only queries, `for_update=False`)
  - `capacity_engine: CapacityEngine` (pure calculation, Phase 13)
  - `farmer_repo: FarmerRepository` (subject-to-farmer resolution)
- **Core Method**:
  ```python
  async def select_priority_centre(
      self,
      payload: PriorityCentreSelectionRequest,
      current_user: AuthenticatedUser,
  ) -> PriorityCentreSelectionResponse: ...
  ```
- **Read-Only Invariant**:
  - **Zero Database Writes**: No inserts, updates, deletes, flushes, or commits.
  - Repositories remain read-only for this service.
- **Evaluation Loop Flow**:
  1. Validate caller identity and resolve farmer profile.
  2. Validate payload priority sequence and centre uniqueness.
  3. Sort centre preferences by `priority` ascending.
  4. Iterate through preferences:
     - Fetch centre via `centre_repo.get_by_id(centre_id)`. If missing or inactive -> record failure reason, continue.
     - Fetch capacity record via `capacity_repo.get_capacity_record(centre_id, crop_id, ready_date, for_update=False)`. If missing -> record failure reason, continue.
     - Evaluate capacity via `capacity_engine.calculate(total_capacity_kg, allocated_quantity_kg, active)`.
     - Check status: If `metrics.capacity_status == CapacityStatus.INACTIVE` -> record failure reason, continue.
     - Check sufficiency: If `metrics.available_capacity_kg < requested_quantity_kg` -> record failure reason, continue.
     - **Success**: Record selected centre, priority, available capacity, stop evaluation loop immediately.
  5. Assemble and return `PriorityCentreSelectionResponse`.

---

## 6. API Contract

### Endpoint
`POST /api/v1/farmers/me/centre-selection`

### Request Schema (`PriorityCentreSelectionRequest`)
```json
{
  "crop_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "ready_date": "2026-11-15",
  "requested_quantity_kg": "500.00",
  "preferred_centres": [
    {
      "centre_id": "8a6c3e21-5717-4562-b3fc-2c963f66af01",
      "priority": 1
    },
    {
      "centre_id": "9b7d4f32-5717-4562-b3fc-2c963f66af02",
      "priority": 2
    },
    {
      "centre_id": "0c8e5a43-5717-4562-b3fc-2c963f66af03",
      "priority": 3
    }
  ]
}
```

### Response Schema (`PriorityCentreSelectionResponse`)
```json
{
  "success": true,
  "selected_centre_id": "9b7d4f32-5717-4562-b3fc-2c963f66af02",
  "selected_priority": 2,
  "crop_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "ready_date": "2026-11-15",
  "requested_quantity_kg": "500.00",
  "available_capacity_kg": "1200.00",
  "evaluated_centres": [
    {
      "centre_id": "8a6c3e21-5717-4562-b3fc-2c963f66af01",
      "priority": 1,
      "status": "UNAVAILABLE",
      "reason": "Insufficient capacity: 200.00 kg available, 500.00 kg requested."
    },
    {
      "centre_id": "9b7d4f32-5717-4562-b3fc-2c963f66af02",
      "priority": 2,
      "status": "AVAILABLE",
      "reason": "Sufficient capacity available."
    }
  ],
  "message": "Centre 9b7d4f32-5717-4562-b3fc-2c963f66af02 selected with priority 2."
}
```

### All-Unavailable Response (`200 OK` or Domain Error Representation)
```json
{
  "success": false,
  "selected_centre_id": null,
  "selected_priority": null,
  "crop_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "ready_date": "2026-11-15",
  "requested_quantity_kg": "500.00",
  "available_capacity_kg": null,
  "evaluated_centres": [
    {
      "centre_id": "8a6c3e21-5717-4562-b3fc-2c963f66af01",
      "priority": 1,
      "status": "UNAVAILABLE",
      "reason": "Insufficient capacity: 200.00 kg available, 500.00 kg requested."
    },
    {
      "centre_id": "9b7d4f32-5717-4562-b3fc-2c963f66af02",
      "priority": 2,
      "status": "UNAVAILABLE",
      "reason": "Procurement centre is inactive."
    }
  ],
  "message": "No preferred centre available satisfying the requested quantity."
}
```

---

## 7. Validation Rules

1. `requested_quantity_kg > 0`: Must be strictly positive.
2. `preferred_centres` non-empty: At least 1 centre preference required.
3. `priority >= 1`: Minimum priority value is 1.
4. Priority Sequence & Uniqueness:
   - Priorities within the request must be strictly unique.
   - Distinct priorities set must equal consecutive integers `{1, ..., N}` (starts at 1 without gaps or duplicates).
5. Centre ID Uniqueness:
   - No centre ID can appear more than once in the preference list.
6. Validation Failures:
   - Handled via Pydantic model validation / FastAPI request parsing returning `422 Unprocessable Entity`.

---

## 8. Authorization

- **Role**: Restricted to `Role.FARMER` (or `Role.OFFICER` acting within proper context).
- **Farmer Profile Check**:
  - `user.farmer_id` must exist for authenticated farmer user.
  - Farmers may only evaluate centre selection for their own farmer profile.
  - Cross-farmer access is strictly prohibited.
- **Officer Boundaries**:
  - No officer mutation endpoints added.

---

## 9. Test Plan

Comprehensive test coverage across unit, service, and API integration layers in `tests/test_priority_centre_service.py` and `tests/test_priority_centre_api.py`:

1. **Priority 1 Available**: Selected immediately; lower priorities not evaluated.
2. **Priority 1 Unavailable, Priority 2 Available**: Selected correctly; Priority 1 failure recorded; Priority 3+ unvisited.
3. **First Two Unavailable, Priority 3 Available**: Priority 3 selected; prior failures recorded.
4. **All Preferred Centres Unavailable**: Domain failure returned; all failures reported; zero selection.
5. **Priority Order Respected**: Evaluated in exact order of ascending priority regardless of list order in JSON payload.
6. **Short-Circuit Evaluation**: Mock assertions confirm repository/engine are never called for centres with priority > selected priority.
7. **Duplicate Centre Rejected**: Payload with repeated centre IDs returns HTTP 422.
8. **Duplicate Priority Rejected**: Payload with repeated priority numbers returns HTTP 422.
9. **Priority Starting Constraint**: Priorities starting at 0, 2, or with gaps return HTTP 422.
10. **Inactive Centre Skipped**: Centre with `active=False` is properly skipped.
11. **Missing Capacity Record Skipped**: Uninitialized capacity record is properly skipped.
12. **Insufficient Capacity Skipped**: Capacity record with `available < requested` is properly skipped.
13. **Sufficient Capacity Selected**: Exact boundary (`available == requested`) and headroom (`available > requested`) properly selected.
14. **Farmer Authorization**: Unauthenticated (401) and non-farmer users (403) blocked.
15. **Zero Database Mutation Verification**: Verified that no session commits, flushes, inserts, or updates occur during evaluation.

---

## 10. Explicit Non-Goals

- **NO** database schema modifications.
- **NO** creation of `booking_requests` table.
- **NO** creation of `booking_request_centre_preferences` table.
- **NO** creation of `slots` table.
- **NO** creation of `slot_bookings` table.
- **NO** Alembic migration `0008`.
- **NO** changes to `procurement_intents` columns or constraints.
- **NO** changes to `allocation_runs` or `allocation_decisions`.
- **NO** changes to `capacity_records` schema.
- **NO** repurposing of `procurement_tokens`.
- **NO** manual creation of `AllocationDecision` or bypassing Phase 14 `AllocationEngine`.
- **NO** manual approval of `ProcurementIntent`.
- **NO** external systems (SMS, IVR, Redis, WebSockets, offline sync, ML).

---

## 11. Migration Impact

- **Zero Migrations Required**.
- Current local migration head remains: **`0007`**.
- Live Supabase database requires zero DDL changes.
- `alembic check` remains clean with no schema drift.

---

## 12. Verification Plan

All checks must pass without errors:
1. `ruff check .`
2. `ruff format --check .`
3. `mypy app tests`
4. `alembic check`
5. `pytest -q -ra`

---

## 13. Final Readiness

The scope is strictly corrected to a read-only Priority Centre Selection service and API. Zero database modifications or migrations are included. Execution is blocked pending user approval.
