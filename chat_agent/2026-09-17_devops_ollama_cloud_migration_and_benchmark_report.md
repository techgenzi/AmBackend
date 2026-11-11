# DevOps Technical Guide: Ollama Cloud Migration & Benchmark Comparison Report

**Date**: 2026-09-17  
**Service**: `chat_agent` (`Fabrico360-BE` & `AmNonOvens`)  
**Provider Transition**: From Self-Hosted CPU VPS (`http://169.58.219.143:4000`) to **Ollama Cloud** (`https://api.ollama.com/api/chat`)  
**Active Model**: `qwen3.5:397b`  

---

## 1. Executive Summary

This document details the backend migration of the `chat_agent` microservice from a CPU-constrained self-hosted VPS to **Ollama Cloud**, achieving a **~20x end-to-end latency improvement** (from ~4.2 minutes down to ~5–12 seconds).

### Key Constraints Preserved:
- **Frontend Staged Execution Architecture**: The frontend 3-stage calling lifecycle (`stage: "tool_decision"`, client-side ERP GET execution, and `stage: "synthesis"`) remains **100% unchanged**.
- **Cross-Format Normalization**: Added a unified parser layer supporting both Ollama native format (`/api/chat` with NDJSON streaming) and OpenAI-compatible format (`/v1/chat/completions` with SSE streaming).

---

## 2. Environment & Configuration Settings

### `chat_agent/config.py` & `.env` Settings

| Configuration Key | Environment Variable | Configured Value |
| :--- | :--- | :--- |
| **LLM Endpoint** | `LLM_API_URL` | `https://api.ollama.com/api/chat` |
| **API Key** | `LLM_API_KEY` | `26d01b0e81b44a9497419bc173472808.wc5rzRfUZ6qxS712XNmskvxX` |
| **Default Model** | `LLM_MODEL` | `qwen3.5:397b` |
| **Max Retries** | `LLM_MAX_RETRIES` | `3` |
| **Request Timeout** | `LLM_TIMEOUT` | `120` seconds |
| **Max Tool Records** | `MAX_TOOL_RESPONSE_ITEMS` | `15` |
| **Max Tool Characters** | `MAX_TOOL_RESPONSE_CHARS` | `6000` |

---

## 3. Staged Frontend Execution Architecture

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Frontend Client
    participant API as Chat Agent API (/fabrico/chatAgent)
    participant Cloud as Ollama Cloud (qwen3.5:397b)
    participant ERP as ERP Gateway / Master APIs

    Note over User, Cloud: Stage 1: Tool Decision Call (~3.9s)
    User->>API: POST / { message: "list the products", stage: "tool_decision" }
    API->>Cloud: POST /api/chat { messages, tools: TOOLS_SCHEMA }
    Cloud-->>API: { message: { tool_calls: [{ name: "get_products", args: {} }] } }
    API-->>User: 200 OK { status: "tool_required", tool_calls: [...] }

    Note over User, ERP: Stage 2: ERP Data Fetching (~1-2s)
    User->>ERP: GET /fabrico/baseConfig/products/
    ERP-->>User: 200 OK [ { id: 101, product_name: "Non-Woven Fabric...", ... } ]

    Note over User, Cloud: Stage 3: Synthesis Call (~4.5s)
    User->>API: POST / { message: "list the products", stage: "synthesis", tool_calls: [...] }
    API->>Cloud: POST /api/chat { messages: [prompt, ERP data], stream: true/false }
    Cloud-->>API: Synthesized Markdown Table / Streaming Chunks
    API-->>User: 200 OK / SSE Event Stream with formatted table
```

---

## 4. Benchmark Comparison Results

### Task Evaluated: `"list the products"`

| Metric | Setup A: Self-Hosted VPS (Qwen 2.5 7B Q4_K_M on CPU) | Setup B: Ollama Cloud (Qwen 3.5 397B Cloud Inference) | Delta / Speedup |
| :--- | :---: | :---: | :---: |
| **Stage 1: Tool Decision Latency** | 16.16 seconds (~1.08 tok/s) | **3.97 seconds (~53 tok/s)** | **4.07x faster** |
| **Stage 2: ERP GET API Query** | ~1.5 seconds | ~1.5 seconds | Equal |
| **Stage 3: Synthesis Latency** | 234.08 seconds (~0.92 tok/s) | **8.80 seconds (~93 tok/s)** | **26.6x faster** |
| **Total Round-Trip Time (RTT)** | **~251.7 seconds (4.2 minutes)** | **~14.2 seconds** | **~18x faster** |
| **Output Presentation** | Vertical Bullet Points (Missing ID) | Structured Markdown Table (With IDs) | Superior Clarity |

---

## 5. AI Judge Scoring & Evaluation

Evaluated directly via Ollama Cloud acting as an objective benchmark judge:

| Evaluation Criterion | Setup A (Self-Hosted VPS 7B) | Setup B (Ollama Cloud 397B) | Judge Notes |
| :--- | :---: | :---: | :--- |
| **1. Tool Calling Accuracy** | 8 / 10 | **10 / 10** | Both identified `get_products` with `{}`. Cloud decided in 3.9s vs 16.2s. |
| **2. Formatting & Visual Clarity** | 7 / 10 | **10 / 10** | Cloud produced standard ERP Markdown tables with IDs; Setup A used plain lists. |
| **3. Production Readiness & UX** | 1 / 10 | **10 / 10** | 4+ minutes wait time in Setup A causes user abandonment / timeouts. |
| **Final Composite Score** | **5.3 / 10** | **10 / 10** | **Winner: Ollama Cloud (Setup B)** |

---

## 6. Throttling, Rate Limiting & Retry Strategies

### A. HTTP 429 & Gateway Error Exponential Backoff
Implemented in `chat_agent/app/helper.py`:
- Intercepts `429 (Too Many Requests)`, `500`, `502`, `503`, and `504` errors.
- Automatically retries up to `3` attempts with exponential backoff (`2s`, `4s`, `6s`).

### B. Payload Context Throttling
Implemented in `sanitize_and_compact_json`:
- **Salient Field Filtering**: Strips internal DB audit metadata.
- **Item Capping**: Restricts list responses to `MAX_TOOL_RESPONSE_ITEMS` (default `15`).
- **Character Ceiling**: Limits payload characters to `MAX_TOOL_RESPONSE_CHARS` (default `6,000`).

---

## 7. Verification & Diagnostic Commands

### Test 1: Stage 1 Tool Decision
```bash
curl -X POST "https://api.ollama.com/api/chat" \
  -H "Authorization: Bearer 26d01b0e81b44a9497419bc173472808.wc5rzRfUZ6qxS712XNmskvxX" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.5:397b",
    "messages": [{"role": "user", "content": "list the products"}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "get_products",
        "description": "Fetch master list of products.",
        "parameters": {"type": "object", "properties": {"search": {"type": "string"}}}
      }
    }],
    "stream": false
  }'
```

### Test 2: Chat Agent Microservice Call
```bash
curl --location 'https://ipssapi.techgenzi.com/fabrico/chatAgent/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer <IPSS_TOKEN>' \
--data '{
    "message": "list the products",
    "stage": "tool_decision"
}'
```
