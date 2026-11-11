-- Migration: Support Item-Level GRN QC and Product-Based QC
-- Date: 2026-10-16

-- 1. Add is_qc_done and qc_status to grnlineitems if they don't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'grnlineitems' AND column_name = 'is_qc_done'
    ) THEN
        ALTER TABLE public.grnlineitems ADD COLUMN is_qc_done BOOLEAN DEFAULT FALSE;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'grnlineitems' AND column_name = 'qc_status'
    ) THEN
        ALTER TABLE public.grnlineitems ADD COLUMN qc_status VARCHAR(50) DEFAULT 'PENDING';
    END IF;
END $$;

-- 2. Backfill existing completed GRNs so their line items reflect is_qc_done = TRUE
UPDATE public.grnlineitems gli
SET is_qc_done = TRUE, qc_status = 'COMPLETED'
FROM public.grnotes grn
WHERE gli.grnotesid = grn.grnotesid
  AND grn.is_qc_done = TRUE
  AND (gli.is_qc_done IS NULL OR gli.is_qc_done = FALSE);

-- 3. Create index for fast pending QC queries
CREATE INDEX IF NOT EXISTS idx_grnlineitems_qc_pending 
ON public.grnlineitems(product_id, is_qc_done) 
WHERE deleted IS NOT TRUE;
