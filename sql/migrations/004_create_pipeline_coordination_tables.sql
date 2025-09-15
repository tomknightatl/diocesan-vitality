-- Migration: Create pipeline coordination tables for distributed scaling
-- This enables multiple pipeline pods to coordinate work without conflicts

-- Pipeline workers table to track active worker pods
CREATE TABLE IF NOT EXISTS pipeline_workers (
    worker_id TEXT PRIMARY KEY,
    pod_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'failed')),
    last_heartbeat TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    assigned_dioceses INTEGER[] DEFAULT ARRAY[]::INTEGER[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Diocese work assignments table to track which worker is processing which diocese
CREATE TABLE IF NOT EXISTS diocese_work_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    diocese_id INTEGER NOT NULL REFERENCES "Dioceses"(id),
    worker_id TEXT NOT NULL REFERENCES pipeline_workers(worker_id),
    status TEXT NOT NULL CHECK (status IN ('processing', 'completed', 'failed')),
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    estimated_completion TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_pipeline_workers_status ON pipeline_workers(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_workers_heartbeat ON pipeline_workers(last_heartbeat);
CREATE INDEX IF NOT EXISTS idx_diocese_assignments_status ON diocese_work_assignments(status);
CREATE INDEX IF NOT EXISTS idx_diocese_assignments_diocese ON diocese_work_assignments(diocese_id);
CREATE INDEX IF NOT EXISTS idx_diocese_assignments_worker ON diocese_work_assignments(worker_id);

-- Update trigger for pipeline_workers
CREATE OR REPLACE FUNCTION update_pipeline_workers_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_pipeline_workers_updated_at
    BEFORE UPDATE ON pipeline_workers
    FOR EACH ROW
    EXECUTE FUNCTION update_pipeline_workers_updated_at();

-- Comments for documentation
COMMENT ON TABLE pipeline_workers IS 'Tracks active pipeline worker pods for coordination';
COMMENT ON TABLE diocese_work_assignments IS 'Tracks which worker is processing which diocese to prevent conflicts';
COMMENT ON COLUMN pipeline_workers.worker_id IS 'Unique identifier for each pipeline worker pod';
COMMENT ON COLUMN pipeline_workers.pod_name IS 'Kubernetes pod name for debugging';
COMMENT ON COLUMN pipeline_workers.status IS 'Current status: active, inactive, or failed';
COMMENT ON COLUMN pipeline_workers.last_heartbeat IS 'Last time this worker sent a heartbeat';
COMMENT ON COLUMN diocese_work_assignments.diocese_id IS 'ID of the diocese being processed';
COMMENT ON COLUMN diocese_work_assignments.worker_id IS 'ID of the worker processing this diocese';
COMMENT ON COLUMN diocese_work_assignments.status IS 'Processing status: processing, completed, or failed';