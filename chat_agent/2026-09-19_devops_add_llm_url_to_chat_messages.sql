-- ==============================================================================
-- Database Migration: Add llm_url column to fabrico_chat_messages
-- Service: AI Chat Agent (Fabrico360-BE / AmNonOvens)
-- Date: 2026-09-19
-- Target Database: ipss_db (PostgreSQL)
-- Table Name: fabrico_chat_messages
-- ==============================================================================

-- 1. Add llm_url column if not exists
ALTER TABLE fabrico_chat_messages 
ADD COLUMN IF NOT EXISTS llm_url VARCHAR(500);

-- 2. Performance Index for Provider and Model filtering
CREATE INDEX IF NOT EXISTS idx_fabrico_chat_messages_provider_model 
ON fabrico_chat_messages(provider, model);

-- Verification Query:
-- SELECT column_name, data_type, character_maximum_length 
-- FROM information_schema.columns 
-- WHERE table_name = 'fabrico_chat_messages' AND column_name = 'llm_url';
