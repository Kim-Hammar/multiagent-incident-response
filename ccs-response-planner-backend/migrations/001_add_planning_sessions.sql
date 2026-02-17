-- Migration: Add planning_sessions table
-- Run this manually or via a migration tool

CREATE TABLE IF NOT EXISTS planning_sessions (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    conversation_history JSONB NOT NULL DEFAULT '[]'::jsonb,
    pending_proposal JSONB,
    incident_inputs JSONB NOT NULL,
    agent_config JSONB NOT NULL,
    context_usage JSONB,
    ui_state JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_planning_sessions_username_status
ON planning_sessions (username, status);
