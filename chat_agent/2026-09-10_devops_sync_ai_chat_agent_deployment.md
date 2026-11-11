# DevOps Deployment Instructions: AI Chat Agent Microservice

This document outlines the deployment instructions and environment configurations for running the `chat_agent` service in staging or production.

---

## 1. Environment Variables Configuration

Create or update the `.env` file in the deployment root or Docker environment:

```ini
# ==========================================
# Core App & Database
# ==========================================
PORT=5005
PROD_DB_URL=postgresql+psycopg2://ipss:MBeQ66bqRfNAcFU3@139.59.83.9:5434/ipss_db
REDIS_DB_URL=redis://localhost:6379/0
BASE_URL=https://ipssapi.techgenzi.com

# ==========================================
# Quantized LLM (Qwen 2.5-7B) Endpoint
# ==========================================
LLM_API_URL=http://169.58.219.143:4000/v1/chat/completions
LLM_API_KEY=sk-tiWDcPn6lvsIjLnr5ZjebQ
LLM_MODEL=qwen-2.5-7b
LLM_MAX_RETRIES=3
LLM_TIMEOUT=120

# ==========================================
# Quantized Model Safety & Context Bounds
# ==========================================
MAX_TOOL_RESPONSE_ITEMS=15
MAX_TOOL_RESPONSE_CHARS=6000
```

---

## 2. Database Schema Setup (`fabrico_chat_messages`)

Execute the table creation DDL on the PostgreSQL instance before starting the service:

```sql
CREATE TABLE IF NOT EXISTS fabrico_chat_messages (
    message_id SERIAL PRIMARY KEY,
    user_id BIGINT,
    company_code INTEGER,
    compcode VARCHAR(50),
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

CREATE INDEX IF NOT EXISTS idx_fabrico_chat_messages_company_code ON fabrico_chat_messages(company_code);
CREATE INDEX IF NOT EXISTS idx_fabrico_chat_messages_compcode_user ON fabrico_chat_messages(compcode, user_id);
CREATE INDEX IF NOT EXISTS idx_fabrico_chat_messages_created_on ON fabrico_chat_messages(created_on DESC);
CREATE INDEX IF NOT EXISTS idx_fabrico_chat_messages_deleted ON fabrico_chat_messages(deleted) WHERE deleted = FALSE;
```

---

## 3. Docker Deployment

### Step 1: Build Docker Image
```bash
cd /path/to/Fabrico360-BE/chat_agent
docker build -t fabrico-chat-agent:latest .
```

### Step 2: Run Docker Container
```bash
docker run -d \
  --name fabrico-chat-agent \
  --restart unless-stopped \
  -p 5015:5015 \
  --env-file .env \
  fabrico-chat-agent:latest
```

---

## 4. Direct Host / Systemd Service (Non-Docker Alternative)

### Systemd Service File: `/etc/systemd/system/fabrico-chat-agent.service`

```ini
[Unit]
Description=Fabrico360 AI Chat Agent Service
After=network.target

[Service]
User=api
WorkingDirectory=/home/api/Fabrico360-BE/chat_agent
EnvironmentFile=/home/api/Fabrico360-BE/chat_agent/.env
ExecStart=/home/api/Fabrico360-BE/chat_agent/venv/bin/gunicorn --bind 0.0.0.0:5015 --workers 3 --timeout 180 wsgi:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Enable & Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable fabrico-chat-agent
sudo systemctl start fabrico-chat-agent
sudo systemctl status fabrico-chat-agent
```

---

## 5. API Gateway / Nginx Reverse Proxy Configuration

The microservice runs inside the unified `amdev_deployment` container on port `5005` under supervisord (`Chatagent_API`), reverse proxied by internal Nginx:

```nginx
location /fabrico/chatAgent {
    proxy_pass http://127.0.0.1:5005;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Tool calling with synthesis can take 15-45s on quantized models
    proxy_read_timeout 180s;
    proxy_connect_timeout 180s;
    proxy_send_timeout 180s;
}

location = /fabrico/chatAgent/swagger.json {
    proxy_pass http://127.0.0.1:5005/swagger.json;
}
```

---

## 6. Health Check & Verification

Run a curl test against the deployed instance:

```bash
curl --location 'https://ipssapi.techgenzi.com/fabrico/chatAgent/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer <IPSS_ACCESS_TOKEN>' \
--data '{
    "message": "List available products in inventory"
}'
```
