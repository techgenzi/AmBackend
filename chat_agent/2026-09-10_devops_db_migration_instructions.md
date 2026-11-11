# Database Migration Instructions: AI Chat Agent (`fabrico_chat_messages`)

- **Service**: AI Chat Agent Microservice
- **Target Database**: `ipss_db` (PostgreSQL)
- **Migration SQL File**: [`2026-09-10_devops_chat_messages_table_migration.sql`](./2026-09-10_devops_chat_messages_table_migration.sql)
- **Date**: September 11, 2026

---

## 1. Summary of Changes

The AI Chat service records user prompts, model responses, token counts, tool usage logs, and timestamps. To avoid any table name collision with CRM's existing `chat_messages` table in the shared DEV database, this service uses **`fabrico_chat_messages`**.

### Table Schema (`fabrico_chat_messages`)

| Column | Type | Description |
|---|---|---|
| `message_id` | `SERIAL PRIMARY KEY` | Unique ID for each message turn |
| `user_id` | `BIGINT` | User ID who sent the prompt (64-bit millisecond ID support) |
| `company_code` | `INTEGER` | ERP Company ID (e.g. `company_id`) |
| `compcode` | `VARCHAR(50)` | Alphanumeric tenant company code (e.g. `'CRM'`, `'Test'`) |
| `message` | `TEXT NOT NULL` | User input message / prompt |
| `response` | `TEXT` | LLM synthesized final response |
| `image_url` | `VARCHAR(500)` | Optional uploaded image reference |
| `prompt_tokens` | `INTEGER` | Input tokens consumed |
| `completion_tokens` | `INTEGER` | Output tokens generated |
| `token_cost` | `DOUBLE PRECISION` | Calculated cost ($0.0 for self-hosted LLM) |
| `relevance_score` | `DOUBLE PRECISION` | Response relevance rating |
| `retry_attempts` | `INTEGER` | Number of retries executed |
| `provider` | `VARCHAR(50)` | LLM Provider (`Qwen`) |
| `model` | `VARCHAR(250)` | Model name (`qwen-2.5-7b`) |
| `tools_used` | `TEXT` | JSON array string of invoked tools |
| `created_on` | `TIMESTAMP` | Record creation timestamp |
| `timestamp` | `TIMESTAMP` | Message timestamp |
| `deleted` | `BOOLEAN` | Soft delete flag (`FALSE`) |

---

## 2. Migration Execution Instructions

### Option A: Using `psql` Command Line
```bash
psql -h 139.59.83.9 -p 5434 -U ipss -d ipss_db -f 2026-09-10_devops_chat_messages_table_migration.sql
```

### Option B: Using DBeaver / pgAdmin / GUI
1. Connect to PostgreSQL server (`139.59.83.9:5434`, database: `ipss_db`).
2. Open a SQL Editor tab.
3. Paste and execute the SQL script from [`2026-09-10_devops_chat_messages_table_migration.sql`](./2026-09-10_devops_chat_messages_table_migration.sql).

---

## 3. Verification Queries

Run the following queries to verify successful migration:

```sql
-- 1. Check table existence and columns
\d fabrico_chat_messages;

-- 2. Verify indexes
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'fabrico_chat_messages';

-- 3. Check table readability
SELECT count(*) FROM fabrico_chat_messages;
```

---

## 4. Rollback Plan (If Needed)

```sql
DROP INDEX IF EXISTS idx_fabrico_chat_messages_deleted;
DROP INDEX IF EXISTS idx_fabrico_chat_messages_created_on;
DROP INDEX IF EXISTS idx_fabrico_chat_messages_compcode_user;
DROP INDEX IF EXISTS idx_fabrico_chat_messages_company_code;
DROP TABLE IF EXISTS fabrico_chat_messages;
```
