-- ==============================================================================
-- Migration 0007: Allocation Persistence
-- Target: Externally Managed Supabase PostgreSQL Database
-- ==============================================================================

-- 1. Table: allocation_runs
CREATE TABLE IF NOT EXISTS allocation_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    centre_id UUID NOT NULL REFERENCES procurement_centres(id) ON DELETE CASCADE,
    crop_id UUID NOT NULL REFERENCES crops(id) ON DELETE CASCADE,
    allocation_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_allocation_cycle UNIQUE (centre_id, crop_id, allocation_date)
);

CREATE INDEX IF NOT EXISTS idx_allocation_runs_centre_id ON allocation_runs (centre_id);
CREATE INDEX IF NOT EXISTS idx_allocation_runs_crop_id ON allocation_runs (crop_id);
CREATE INDEX IF NOT EXISTS idx_allocation_runs_date ON allocation_runs (allocation_date);

-- 2. Table: allocation_decisions
CREATE TABLE IF NOT EXISTS allocation_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    allocation_run_id UUID NOT NULL REFERENCES allocation_runs(id) ON DELETE CASCADE,
    intent_id UUID NOT NULL REFERENCES procurement_intents(id) ON DELETE CASCADE,
    farmer_id UUID NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
    requested_quantity_kg NUMERIC NOT NULL,
    allocated_quantity_kg NUMERIC NOT NULL,
    remaining_capacity_kg NUMERIC NOT NULL,
    selected BOOLEAN NOT NULL,
    rank INTEGER NOT NULL,
    ordering_reason TEXT NOT NULL,
    tie_break_digest TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_allocation_run_intent UNIQUE (allocation_run_id, intent_id)
);

CREATE INDEX IF NOT EXISTS idx_allocation_decisions_run_id ON allocation_decisions (allocation_run_id);
CREATE INDEX IF NOT EXISTS idx_allocation_decisions_intent_id ON allocation_decisions (intent_id);
CREATE INDEX IF NOT EXISTS idx_allocation_decisions_farmer_id ON allocation_decisions (farmer_id);
