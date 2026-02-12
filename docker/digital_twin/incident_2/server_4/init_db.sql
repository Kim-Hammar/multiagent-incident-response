-- Create application user with SUPERUSER (misconfiguration for CTF)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_svc') THEN
        CREATE USER app_svc WITH SUPERUSER PASSWORD 'SuperSecret123!';
    END IF;
END
$$;

-- Create CRM production database
SELECT 'CREATE DATABASE crm_production OWNER app_svc'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'crm_production');
\gexec

\c crm_production

-- Create customers table
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed sample data
INSERT INTO customers (name, email, phone) VALUES
    ('Alice Johnson', 'alice@example.com', '+1-555-0101'),
    ('Bob Smith', 'bob@example.com', '+1-555-0102'),
    ('Carol Williams', 'carol@example.com', '+1-555-0103')
ON CONFLICT DO NOTHING;
