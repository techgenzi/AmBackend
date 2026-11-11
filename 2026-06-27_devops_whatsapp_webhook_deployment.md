# DevOps & Database Deployment Instructions - WhatsApp Webhook Integration
**Date:** 2026-06-27

This document provides database schema scripts, environment variables configuration, and deployment procedures to launch the multi-tenant WhatsApp Webhook in the Development and Production environments.

---

## 1. Database Schema Migration Script

Run this SQL script against the database to set up the necessary config and monitoring log tables.

```sql
-- Up Migration
BEGIN;

-- Table to store Tenant-wise WhatsApp App credentials
CREATE TABLE IF NOT EXISTS whatsapp_tenant_configs (
    id SERIAL PRIMARY KEY,
    tenant_id INT NOT NULL,
    compcode VARCHAR(10) NOT NULL,
    phone_number_id VARCHAR(50) UNIQUE NOT NULL,
    waba_id VARCHAR(50) NOT NULL,
    system_user_access_token TEXT NOT NULL,
    display_phone_number VARCHAR(20),
    status VARCHAR(20) DEFAULT 'Active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table to log incoming messages for monitoring and troubleshooting
CREATE TABLE IF NOT EXISTS whatsapp_incoming_messages (
    id SERIAL PRIMARY KEY,
    message_sid VARCHAR(100) UNIQUE NOT NULL,
    tenant_id INT NOT NULL,
    compcode VARCHAR(10) NOT NULL,
    sender_mobile VARCHAR(20) NOT NULL,
    raw_text TEXT NOT NULL,
    message_type VARCHAR(20) DEFAULT 'Unknown', -- 'Chat' or 'Order'
    extracted_json JSONB,
    status VARCHAR(20) DEFAULT 'Pending', -- 'Pending', 'Parsed', 'Failed', 'Ignored'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices for performance on routing lookups
CREATE INDEX IF NOT EXISTS idx_whatsapp_tenant_phone ON whatsapp_tenant_configs(phone_number_id);
CREATE INDEX IF NOT EXISTS idx_whatsapp_msg_tenant ON whatsapp_incoming_messages(tenant_id, compcode);

COMMIT;
```

### Seed Simulation Data (2 Tenants)
Execute these inserts in your testing database to simulate the environment routing:

```sql
-- Tenant 1: Demo (tenant_id = 1, compcode = 'Demo')
INSERT INTO whatsapp_tenant_configs (tenant_id, compcode, phone_number_id, waba_id, system_user_access_token, display_phone_number, status)
VALUES (1, 'Demo', '11111', 'waba_demo_01', 'token_demo_xyz', '+919876543210', 'Active')
ON CONFLICT (phone_number_id) DO NOTHING;

-- Tenant 2: Cake Waves (tenant_id = 127, compcode = 'CW')
INSERT INTO whatsapp_tenant_configs (tenant_id, compcode, phone_number_id, waba_id, system_user_access_token, display_phone_number, status)
VALUES (127, 'CW', '22222', 'waba_cakewaves_02', 'token_cakewaves_abc', '+918765432109', 'Active')
ON CONFLICT (phone_number_id) DO NOTHING;
```

---

## 2. Environment Variables Configuration

Add these variables to your environment configuration (`.env` or server container):

```bash
# Groq LLM configurations
GROQ_API_KEY="gsk_your_groq_api_key_here"

# Webhook secret verified by Meta Cloud API
WHATSAPP_VERIFY_TOKEN="techgenzi_verify_token_secure_xyz"
```

---

## 3. Deployment Steps

### A. Development Environment
1. **Apply Migration**: Run the SQL schema script on your local Postgres instance.
2. **Local Tunnel**: Use `ngrok` or any local tunnel solution to expose your local Flask service port to the web:
   ```bash
   ngrok http 5000
   ```
3. **Configure Webhook**: Paste the generated HTTPS ngrok URL into your Meta Developers Dashboard:
   - *Callback URL*: `https://<subdomain>.ngrok.app/am-customer-purchase-order/am-whatsapp/webhook`
   - *Verify Token*: `techgenzi_verify_token_secure_xyz`

### B. Production Environment
1. **Deploy Migration**: Execute the SQL scripts on your production database during the maintenance window.
2. **Inject Secrets**: Set `GROQ_API_KEY` and `WHATSAPP_VERIFY_TOKEN` securely using Docker environment variables, Kubernetes Secrets, or your Cloud Provider's key vault.
3. **Update SSL Rules**: Ensure the reverse proxy (Nginx/HAProxy) allows TLS 1.2+ for incoming webhook endpoints to guarantee safe transport of WhatsApp customer payloads.
4. **Publish Meta App**: Submit the `techgenzi-order--integration` app for live production traffic in the Meta App console.
