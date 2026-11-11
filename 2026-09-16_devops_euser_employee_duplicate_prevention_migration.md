# DevOps Migration: EUser Employee Duplicate Prevention & Index Optimization

**Date:** 2026-09-16  
**Target Services:** UserRole, HRM-Backend-All (employees), Fabrico360 / OmniPlus  
**SQL File:** `2026-09-16_devops_euser_employee_duplicate_prevention_migration.sql`

---

## 1. Problem Statement & Motivation
In the Fabrico360 / OmniPlus system, employee onboarding is managed by the HR team in HRM (`hremploymast`), whereas application access provisioning is governed by the Admin in User Management (`userstab` / `euser`).

To prevent orphaned accounts, duplicate identities under varying usernames, and multiple accounts linked to the same employee:
1. Active user records in `euser` must have at most **one active user per employee** (`emp_id`).
2. Fast duplicate check capabilities are needed across `emailid`, `emp_id`, and `username`.
3. Join operations between employee records and user accounts require performant indexing.

---

## 2. Database Changes
1. **Partial Unique Index (`uq_euser_active_emp_id`)**:
   - Ensures PostgreSQL guarantees at the database level that no two active users (`deleted IS NOT TRUE`) can share the same `emp_id`.
   - Allows multiple `NULL` values so non-employee accounts remain unaffected.
2. **Functional Case-Insensitive Index (`idx_euser_active_emailid_lower`)**:
   - Accelerates lookups for duplicate email addresses (`LOWER(emailid)`) during user creation and pre-flight validation for active users.
3. **Lookup Index (`idx_euser_emp_id`)**:
   - Speeds up joins between `hremploymast` (`hremploymastid`) and `euser` (`emp_id`).
4. **Functional Case-Insensitive Index (`idx_euser_username_lower`)**:
   - Accelerates case-insensitive username checks (`LOWER(username)`) during login and user creation.

---

## 3. Deployment Instructions

### Pre-Deployment Verification:
Check if there are any existing duplicate assignments in active user rows:
```sql
-- Verify employee duplicate assignments
SELECT emp_id, count(*) 
FROM euser 
WHERE emp_id IS NOT NULL AND deleted IS NOT TRUE 
GROUP BY emp_id 
HAVING count(*) > 1;

-- Verify email duplicate assignments (optional audit)
SELECT LOWER(emailid), count(*) 
FROM euser 
WHERE emailid IS NOT NULL AND deleted IS NOT TRUE 
GROUP BY LOWER(emailid) 
HAVING count(*) > 1;
```
If duplicate active `emp_id` rows exist, merge or soft-delete extraneous records prior to running the migration.

### Execution:
```bash
psql -h <DB_HOST> -U <DB_USER> -d <DB_NAME> -f 2026-09-16_devops_euser_employee_duplicate_prevention_migration.sql
```

---

## 4. Rollback Plan
```sql
DROP INDEX IF EXISTS uq_euser_active_emp_id;
DROP INDEX IF EXISTS idx_euser_active_emailid_lower;
DROP INDEX IF EXISTS idx_euser_emp_id;
DROP INDEX IF EXISTS idx_euser_username_lower;
```
