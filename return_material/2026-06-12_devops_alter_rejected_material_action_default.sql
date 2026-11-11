-- Alter the default value constraint for action on rejected_material to 'Return to Store'
ALTER TABLE rejected_material ALTER COLUMN action SET DEFAULT 'Return to Store';

-- Update any accidental records that might have been inserted during testing
UPDATE rejected_material SET action = 'Return to Store' WHERE action = 'Return to Vendor';
