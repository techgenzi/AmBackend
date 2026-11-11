-- Migration: DevOps EUser Employee Duplicate Prevention & Index Migration
-- Date: 2026-09-16
-- Purpose:
-- 1. Enforce partial unique index on euser(emp_id) so that no two active users can map to the same employee.
-- 2. Create case-insensitive functional index on euser(LOWER(emailid)) for fast email duplicate lookups.
-- 3. Create index on euser(emp_id) for foreign key joins and general employee lookups.
-- 4. Create case-insensitive index on euser(LOWER(username)) for active user authentication and uniqueness checks.

BEGIN;

-- 1. Pre-migration verification queries (run manually before executing migration if needed):
-- SELECT emp_id, count(*) FROM euser WHERE emp_id IS NOT NULL AND deleted IS NOT TRUE GROUP BY emp_id HAVING count(*) > 1;
-- SELECT LOWER(emailid), count(*) FROM euser WHERE emailid IS NOT NULL AND deleted IS NOT TRUE GROUP BY LOWER(emailid) HAVING count(*) > 1;

-- 2. Create partial unique index on emp_id for active users
CREATE UNIQUE INDEX IF NOT EXISTS uq_euser_active_emp_id 
ON euser (emp_id) 
WHERE emp_id IS NOT NULL AND deleted IS NOT TRUE;

-- 3. Create case-insensitive index on emailid for active users
CREATE INDEX IF NOT EXISTS idx_euser_active_emailid_lower 
ON euser (LOWER(emailid)) 
WHERE emailid IS NOT NULL AND deleted IS NOT TRUE;

-- 4. Create index on emp_id for soft-deleted / general lookups
CREATE INDEX IF NOT EXISTS idx_euser_emp_id 
ON euser (emp_id);

-- 5. Create index on username case-insensitive lookups for active users
CREATE INDEX IF NOT EXISTS idx_euser_username_lower 
ON euser (LOWER(username)) 
WHERE deleted IS NOT TRUE;

COMMIT;
