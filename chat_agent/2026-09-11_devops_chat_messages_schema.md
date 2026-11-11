# Database Migration: AI Chat Messages Schema (`fabrico_chat_messages`)

**Date**: 2026-09-11  
**Target Table**: `fabrico_chat_messages`  
**Objective**: Create the multi-tenant `fabrico_chat_messages` table to persist AI chat logs, prompt/completion token usage, tool invocations, tenant identifiers, and query response metadata without colliding with CRM's existing `chat_messages` table in the shared database.

---

## 1. Migration DDL Script

Run the following SQL script in PostgreSQL (`ipss_db`):

```sql
-- 1. Create fabrico_chat_messages table
CREATE TABLE IF NOT EXISTS fabrico_chat_messages (
    message_id SERIAL PRIMARY KEY,
    user_id BIGINT,                                -- BIGINT to support 64-bit millisecond user IDs (e.g. 1582536975861)
    company_code INTEGER,                          -- Numeric company ID (e.g. 67, 28)
    compcode VARCHAR(50),                          -- Alphanumeric company/tenant code (e.g. 'CRM', 'Test', 'AmNonOvens')
    message TEXT NOT NULL,
    response TEXT,
    image_url VARCHAR(500),
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    token_cost DOUBLE PRECISION DEFAULT 0.0,
    relevance_score DOUBLE PRECISION DEFAULT 0.0,
    retry_attempts INTEGER DEFAULT 0,
    provider VARCHAR(50) DEFAULT 'Qwen',
    model VARCHAR(250) DEFAULT 'qwen-2.5-7b',
    tools_used TEXT,
    created_on TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE
);

-- 2. Performance Indexes for multi-tenant and user history queries
CREATE INDEX IF NOT EXISTS idx_fabrico_chat_messages_company_code ON fabrico_chat_messages(company_code);
CREATE INDEX IF NOT EXISTS idx_fabrico_chat_messages_compcode_user ON fabrico_chat_messages(compcode, user_id);
CREATE INDEX IF NOT EXISTS idx_fabrico_chat_messages_created_on ON fabrico_chat_messages(created_on DESC);
CREATE INDEX IF NOT EXISTS idx_fabrico_chat_messages_deleted ON fabrico_chat_messages(deleted) WHERE deleted = FALSE;
```

---

## 2. Table Column Specifications

| Column Name | Data Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `message_id` | `SERIAL` | Auto | Unique primary key for each chat message |
| `user_id` | `BIGINT` | `NULL` | User identifier from JWT token (`userid` / `user_id`) |
| `company_code` | `INTEGER` | `NULL` | Numeric company ID (e.g. `company_id`) |
| `compcode` | `VARCHAR(50)` | `NULL` | Alphanumeric tenant / company code |
| `message` | `TEXT` | - | User prompt / question |
| `response` | `TEXT` | `NULL` | Synthesized AI assistant response |
| `image_url` | `VARCHAR(500)` | `NULL` | Image reference for multimodal queries |
| `prompt_tokens` | `INTEGER` | `0` | Number of tokens in input context |
| `completion_tokens` | `INTEGER` | `0` | Number of tokens in generated answer |
| `token_cost` | `DOUBLE PRECISION` | `0.0` | Cost of tokens ($0.0 for self-hosted LLM) |
| `relevance_score` | `DOUBLE PRECISION` | `0.0` | Optional relevance scoring |
| `retry_attempts` | `INTEGER` | `0` | Retry attempts on API/network error |
| `provider` | `VARCHAR(50)` | `'Qwen'` | LLM provider name |
| `model` | `VARCHAR(250)` | `'qwen-2.5-7b'` | LLM model identifier |
| `tools_used` | `TEXT` | `NULL` | JSON array string of tools invoked (e.g. `["get_product_list"]`) |
| `created_on` | `TIMESTAMP` | `CURRENT_TIMESTAMP` | Record creation timestamp |
| `timestamp` | `TIMESTAMP` | `CURRENT_TIMESTAMP` | Message timestamp |
| `deleted` | `BOOLEAN` | `FALSE` | Soft-delete flag |

---

## 3. Rollback Script

```sql
DROP INDEX IF EXISTS idx_fabrico_chat_messages_deleted;
DROP INDEX IF EXISTS idx_fabrico_chat_messages_created_on;
DROP INDEX IF EXISTS idx_fabrico_chat_messages_compcode_user;
DROP INDEX IF EXISTS idx_fabrico_chat_messages_company_code;
DROP TABLE IF EXISTS fabrico_chat_messages;
```
