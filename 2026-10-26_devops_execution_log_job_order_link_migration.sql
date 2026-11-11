-- ==============================================================================
-- Migration: Associate Job Order at Stage Level in Production Execution
-- File: 2026-10-26_devops_execution_log_job_order_link_migration.sql
-- Date: 2026-10-26
-- Description:
--   1. Adds nullable `job_order_id` (referencing joborder.joborderid) on `execution_log`.
--   2. Adds nullable `vendor_id` (referencing vendor.vendorid) on `execution_log`.
--   3. Adds composite indexes on `execution_log` for fast traceability & audits.
-- ==============================================================================

DO $$
BEGIN
    -- 1. Add job_order_id to execution_log if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'execution_log' AND column_name = 'job_order_id'
    ) THEN
        ALTER TABLE public.execution_log 
        ADD COLUMN job_order_id BIGINT NULL;
        
        COMMENT ON COLUMN public.execution_log.job_order_id IS 'Reference to joborder(joborderid) for outsourced / job-order fulfilled stage executions';
    END IF;

    -- 2. Add vendor_id to execution_log if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'execution_log' AND column_name = 'vendor_id'
    ) THEN
        ALTER TABLE public.execution_log 
        ADD COLUMN vendor_id BIGINT NULL;
        
        COMMENT ON COLUMN public.execution_log.vendor_id IS 'Reference to vendor(vendorid) for outsource vendor fulfilling the stage execution';
    END IF;

    -- 3. Ensure is_outsource flag exists on execution_log
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'execution_log' AND column_name = 'is_outsource'
    ) THEN
        ALTER TABLE public.execution_log 
        ADD COLUMN is_outsource BOOLEAN DEFAULT FALSE;
        
        COMMENT ON COLUMN public.execution_log.is_outsource IS 'Indicates if stage execution was performed by an external Job Order vendor';
    END IF;
END $$;

-- 4. Create Indexes for fast lookups in cost reports and audit trails
CREATE INDEX IF NOT EXISTS idx_execution_log_job_order_id 
ON public.execution_log (compcode, job_order_id) 
WHERE job_order_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_execution_log_vendor_id 
ON public.execution_log (compcode, vendor_id) 
WHERE vendor_id IS NOT NULL;

