-- ==============================================================================
-- ResolveHelm Migration 002: Ticket Notes & Operator Workflow
-- ==============================================================================

-- 1. Add assigned_to column to tickets
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS assigned_to TEXT;

-- 2. Update status check constraint to include 'resolved'
ALTER TABLE tickets DROP CONSTRAINT IF EXISTS tickets_status_check;
ALTER TABLE tickets ADD CONSTRAINT tickets_status_check CHECK (status IN ('open', 'answered', 'escalated', 'closed', 'resolved'));

-- 3. Ticket Notes Table: Internal operator notes for collaborative customer support
CREATE TABLE IF NOT EXISTS ticket_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    author TEXT NOT NULL,
    note TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ticket_notes_ticket_id ON ticket_notes (ticket_id);
CREATE INDEX IF NOT EXISTS idx_ticket_notes_created_at ON ticket_notes (created_at DESC);
