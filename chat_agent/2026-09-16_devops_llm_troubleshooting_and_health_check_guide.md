# DevOps Guide: LLM Health Check, Model Listing, and Troubleshooting

**Date**: 2026-09-16  
**Target Microservice**: `chat_agent` (`Fabrico360-BE`)  
**LLM Host Server**: `http://169.58.219.143:4000` (OpenAI-Compatible Proxy / LiteLLM / vLLM)  
**Configured Model**: `qwen-2.5-7b`  
**Configured API Key**: `sk-tiWDcPn6lvsIjLnr5ZjebQ`  

---

## 1. Quick Reference: Environment Details

| Configuration Key | Environment Variable | Configured Value |
| :--- | :--- | :--- |
| **Base Endpoint** | `LLM_API_URL` | `http://169.58.219.143:4000/v1/chat/completions` |
| **Server Host & Port** | - | `169.58.219.143:4000` |
| **API Key / Secret** | `LLM_API_KEY` | `sk-tiWDcPn6lvsIjLnr5ZjebQ` |
| **Default Model** | `LLM_MODEL` | `qwen-2.5-7b` |
| **Max Timeout** | `LLM_TIMEOUT` | `120` seconds |
| **Max Retries** | `LLM_MAX_RETRIES`| `3` |

---

## 2. Step-by-Step Troubleshooting Workflow

```mermaid
flowchart TD
    A[Start Troubleshooting] --> B[1. Network Connectivity Check]
    B -- Failed (Connection Refused/Timeout) --> B1[Check VPS Firewall / Port 4000 / Service Status]
    B -- Passed --> C[2. Server Health Check]
    C -- Failed (5xx Error) --> C1[Check GPU / CUDA Memory on VPS]
    C -- Passed --> D[3. API Key Validation]
    D -- 401 Unauthorized --> D1[Verify / Update LLM_API_KEY]
    D -- 200 OK --> E[4. List Available Models]
    E -- Model Missing --> E1[Verify Model Name on Proxy/Weights]
    E -- Model Present --> F[5. Chat Completion Test]
    F -- High Latency / Error --> F1[Tune Context / Batch Size / Quantization]
    F -- 200 Success --> G[LLM Server Fully Operational]
```

---

## 3. Diagnostic Commands

### Step 1: Network & Port Connectivity Check
Verify that the VPS IP is reachable and port `4000` is accepting incoming TCP connections:

```bash
# Check TCP Port 4000 connectivity
nc -zv 169.58.219.143 4000
```
* **Expected Output**: `Connection to 169.58.219.143 port 4000 [tcp/*] succeeded!`
* *If it hangs or fails*: Check VPS security group / firewall rules for port `4000`.

---

### Step 2: Server Health & Liveness Check
Test whether the proxy/inference server process is alive:

```bash
# Standard Health Check
curl -s -o /dev/null -w "%{http_code}\n" http://169.58.219.143:4000/health
```

```bash
# Detailed Health Check (LiteLLM / Proxy)
curl -X GET "http://169.58.219.143:4000/health/readiness" \
  -H "Authorization: Bearer sk-tiWDcPn6lvsIjLnr5ZjebQ"
```
* **Expected Output**: HTTP `200` with `{"status": "healthy"}` or `{"healthy": true}`.

---

### Step 3: API Key Validity & Authentication Test
Validate that the `LLM_API_KEY` (`sk-tiWDcPn6lvsIjLnr5ZjebQ`) is recognized by the proxy:

```bash
# Test with Authorized Key (Expected: 200 OK)
curl -i -X GET "http://169.58.219.143:4000/v1/models" \
  -H "Authorization: Bearer sk-tiWDcPn6lvsIjLnr5ZjebQ"
```

```bash
# Test with Invalid Key (Expected: 401 Unauthorized to confirm auth is enforcing)
curl -i -X GET "http://169.58.219.143:4000/v1/models" \
  -H "Authorization: Bearer sk-invalid-key-test"
```

---

### Step 4: List Available Models
Verify that the target model `qwen-2.5-7b` is loaded, routed, and ready to serve inference:

#### A. OpenAI-Standard Model List:
```bash
curl -X GET "http://169.58.219.143:4000/v1/models" \
  -H "Authorization: Bearer sk-tiWDcPn6lvsIjLnr5ZjebQ" \
  -H "Content-Type: application/json"
```

* **Expected Output Format**:
```json
{
  "object": "list",
  "data": [
    {
      "id": "qwen-2.5-7b",
      "object": "model",
      "created": 1726000000,
      "owned_by": "vllm"
    }
  ]
}
```

#### B. LiteLLM Detailed Model Registry:
```bash
curl -X GET "http://169.58.219.143:4000/models" \
  -H "Authorization: Bearer sk-tiWDcPn6lvsIjLnr5ZjebQ"
```

---

### Step 5: End-to-End Chat Completion Test

#### A. Minimal Single-Turn Smoke Test:
```bash
curl -X POST "http://169.58.219.143:4000/v1/chat/completions" \
  -H "Authorization: Bearer sk-tiWDcPn6lvsIjLnr5ZjebQ" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-2.5-7b",
    "messages": [
      {"role": "system", "content": "You are an ERP assistant."},
      {"role": "user", "content": "Respond with the single word: PONG"}
    ],
    "temperature": 0.1,
    "max_tokens": 10
  }'
```
* **Expected Output**:
```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "PONG"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 18,
    "completion_tokens": 2,
    "total_tokens": 20
  }
}
```

#### B. Streaming SSE Test:
```bash
curl -N -X POST "http://169.58.219.143:4000/v1/chat/completions" \
  -H "Authorization: Bearer sk-tiWDcPn6lvsIjLnr5ZjebQ" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-2.5-7b",
    "messages": [
      {"role": "user", "content": "Count from 1 to 5."}
    ],
    "stream": true
  }'
```

---

## 4. Troubleshooting Matrix: Common Errors & Resolutions

| Error / Symptom | Root Cause | Resolution Steps |
| :--- | :--- | :--- |
| **`Connection refused (Failed to connect to 169.58.219.143:4000)`** | • Docker container or inference server stopped.<br>• VPS firewall / security group blocking port `4000`. | 1. SSH into VPS: `ssh root@169.58.219.143`<br>2. Check running processes: `docker ps` or `pm2 list`<br>3. Restart server: `docker restart litellm` or `vllm`<br>4. Open port: `ufw allow 4000/tcp` |
| **`401 Unauthorized` / `Invalid API Key`** | • `LLM_API_KEY` mismatch between `chat_agent/config.py` and LiteLLM proxy config. | 1. Verify master key in VPS `config.yaml` / LiteLLM proxy.<br>2. Update `LLM_API_KEY` in `chat_agent/config.py` or `.env`. |
| **`404 Model Not Found` (`qwen-2.5-7b`)** | • Model name typo in request.<br>• Model failed to load into GPU memory. | 1. Run `curl http://169.58.219.143:4000/v1/models` to view exact model ID.<br>2. Match `LLM_MODEL` in `config.py` to the returned `id`. |
| **`500 Internal Server Error` / `CUDA Out of Memory`** | • GPU VRAM exhausted on VPS during batch inference. | 1. On VPS, check VRAM: `nvidia-smi`<br>2. Reduce `max_model_len` or increase `--gpu-memory-utilization` in vLLM startup flags.<br>3. Restart vLLM instance to flush cache. |
| **Timeout (`Request timed out after 120s`)** | • Heavy concurrent load or massive tool output. | 1. Verify `MAX_TOOL_RESPONSE_CHARS=6000` is active in `config.py`.<br>2. Enable streaming in chat requests to receive immediate TTFT (Time-To-First-Token). |

---

## 5. All-in-One Automated Diagnostics Script

Save and run this diagnostic script locally or in staging to verify LLM server health in one step:

```bash
#!/usr/bin/env bash
# File: diagnose_llm.sh

LLM_HOST="169.58.219.143"
LLM_PORT="4000"
LLM_KEY="sk-tiWDcPn6lvsIjLnr5ZjebQ"
LLM_MODEL="qwen-2.5-7b"

echo "================================================="
echo "   Fabrico360 / AmNonOvens LLM Diagnostics       "
echo "================================================="

echo -n "[1/5] Testing Port Reachability ($LLM_HOST:$LLM_PORT)... "
if nc -z -w 3 $LLM_HOST $LLM_PORT 2>/dev/null; then
    echo "✅ SUCCESS (Port Open)"
else
    echo "❌ FAILED (Port Closed or Unreachable)"
fi

echo -n "[2/5] Testing Health Endpoint... "
HEALTH_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://$LLM_HOST:$LLM_PORT/health")
if [ "$HEALTH_CODE" = "200" ]; then
    echo "✅ SUCCESS (HTTP 200)"
else
    echo "⚠️ Status: HTTP $HEALTH_CODE"
fi

echo -n "[3/5] Testing API Key Validity... "
AUTH_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $LLM_KEY" "http://$LLM_HOST:$LLM_PORT/v1/models")
if [ "$AUTH_CODE" = "200" ]; then
    echo "✅ SUCCESS (Key Authorized)"
else
    echo "❌ FAILED (HTTP $AUTH_CODE - Check API Key)"
fi

echo "[4/5] Available Models on Server:"
curl -s -H "Authorization: Bearer $LLM_KEY" "http://$LLM_HOST:$LLM_PORT/v1/models" | grep -o '"id": *"[^"]*"' || echo "No models returned"

echo ""
echo -n "[5/5] Testing Chat Completion with '$LLM_MODEL'... "
RESPONSE=$(curl -s -X POST "http://$LLM_HOST:$LLM_PORT/v1/chat/completions" \
  -H "Authorization: Bearer $LLM_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"model\": \"$LLM_MODEL\", \"messages\": [{\"role\": \"user\", \"content\": \"ping\"}], \"max_tokens\": 5}")

if echo "$RESPONSE" | grep -q "choices"; then
    echo "✅ SUCCESS"
    echo "Sample Response: $RESPONSE"
else
    echo "❌ FAILED"
    echo "Error: $RESPONSE"
fi

echo "================================================="
```
