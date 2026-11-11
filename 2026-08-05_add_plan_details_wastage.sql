DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'plan_details' AND column_name = 'wastage') THEN
        ALTER TABLE plan_details ADD COLUMN wastage NUMERIC;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'plan_details' AND column_name = 'wastage_per') THEN
        ALTER TABLE plan_details ADD COLUMN wastage_per NUMERIC;
    END IF;
END $$;
