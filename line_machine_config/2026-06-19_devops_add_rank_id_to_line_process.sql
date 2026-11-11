-- DevOps Database Migration: Add rank_id column to line_process table
-- Date: 2026-06-19

ALTER TABLE line_process ADD COLUMN rank_id INTEGER DEFAULT 1;
