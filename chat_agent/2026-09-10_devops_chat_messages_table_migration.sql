-- ==============================================================================
-- Database Migration: Create fabrico_chat_messages Table and Performance Indexes
-- Service: AI Chat Agent (Fabrico360-BE / AmNonOvens)
-- Date: 2026-09-11
-- Target Database: ipss_db (PostgreSQL)
-- Table Name: fabrico_chat_messages (Namespaced to prevent conflict with CRM)
-- ==============================================================================

CREATE TABLE IF NOT EXISTS fabrico_chat_messages (
    message_id SERIAL PRIMARY KEY,
    user_id BIGINT,                                -- 64-bit millisecond user ID support
    company_code INTEGER,                          -- Numeric company ID (e.g. 67, 28)
    compcode VARCHAR(50),                          -- Alphanumeric tenant code (e.g. 'CRM', 'Test')
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

-- ==============================================================================
-- Performance & Multi-Tenant Indexes
-- ==============================================================================
CREATE INDEX IF NOT EXISTS idx_fabrico_chat_messages_company_code 
ON fabrico_chat_messages(company_code);

CREATE INDEX IF NOT EXISTS idx_fabrico_chat_messages_compcode_user 
ON fabrico_chat_messages(compcode, user_id);

CREATE INDEX IF NOT EXISTS idx_fabrico_chat_messages_created_on 
ON fabrico_chat_messages(created_on DESC);

CREATE INDEX IF NOT EXISTS idx_fabrico_chat_messages_deleted 
ON fabrico_chat_messages(deleted) 
WHERE deleted = FALSE;
