# Fabrico360 / AmNonOvens Sync AI Chat Agent

AI Chat microservice supporting OpenAI and Ollama-compatible tool calling across GET APIs in `AmNonOvens` and `Fabrico360-BE` ERP modules using `qwen3.5:397b` on Ollama Cloud.

## Key Features
- **Ollama Cloud & OpenAI Compatible Tool Calling**: Native integration with `https://api.ollama.com/api/chat` and standard `/v1/chat/completions` endpoints.
- **Frontend Staged Execution Architecture**:
  - `stage: "tool_decision"` (Turn-1 decision returning required ERP tools in ~3.9s)
  - `stage: "synthesis"` (Turn-2 synthesis producing formatted tables/summaries in ~4.5s)
  - `stage: "judge"` (Turn-3 automated LLM-as-a-Judge scoring for Tool Calling accuracy and Answer Quality)
- **AI Judge Scoring & Quality Audit**:
  - Scores `tool_calling_score` (0-10) with detailed selection and parameter feedback.
  - Scores `answer_score` (0-10) evaluating correctness, markdown table format, and conciseness.
  - Generates composite `overall_score` and quality `verdict` (EXCELLENT, GOOD, ACCEPTABLE, NEEDS_IMPROVEMENT, POOR).
  - Automatically updates `relevance_score` on stored `fabrico_chat_messages` records when `message_id` is supplied.
- **Quantized-Safe Large JSON Handling**:
  - Whitelists salient business fields.
  - Limits list responses to `MAX_TOOL_RESPONSE_ITEMS` (default: 15).
  - Truncates characters safely to `MAX_TOOL_RESPONSE_CHARS` (default: 6000 chars).
  - Summarizes total counts vs displayed items.
- **Failover & Exponential Retries**: Automatic backoff retries for transient HTTP 429, 502, 503, 504, and network drops.
- **Tenant & Authentication Propagation**: Propagates `Authorization`, `compcode`, and `tenant_id` headers to internal GET requests.

## Environment Variables (`.env`)
```bash
LLM_API_URL=https://api.ollama.com/api/chat
LLM_API_KEY=26d01b0e81b44a9497419bc173472808.wc5rzRfUZ6qxS712XNmskvxX
LLM_MODEL=qwen3.5:397b
LLM_MAX_RETRIES=3
LLM_TIMEOUT=120
BASE_URL=https://ipssapi.techgenzi.com
MAX_TOOL_RESPONSE_ITEMS=15
MAX_TOOL_RESPONSE_CHARS=6000
```

## Documentation & Technical Reports
- [2026-09-18 LLM Benchmark & Latency Optimization Report](file:///Users/rajkumarmuthuramalingam/Work/Fabrico360-BE/chat_agent/2026-09-18_devops_llm_benchmark_and_latency_optimization_report.md)
- [2026-09-17 Ollama Cloud Migration & Benchmark Report](file:///Users/rajkumarmuthuramalingam/Work/Fabrico360-BE/chat_agent/2026-09-17_devops_ollama_cloud_migration_and_benchmark_report.md)
- [2026-09-16 LLM Troubleshooting & Health Check Guide](file:///Users/rajkumarmuthuramalingam/Work/Fabrico360-BE/chat_agent/2026-09-16_devops_llm_troubleshooting_and_health_check_guide.md)
- [2026-09-10 AI Chat Agent Deployment Guide](file:///Users/rajkumarmuthuramalingam/Work/Fabrico360-BE/chat_agent/2026-09-10_devops_sync_ai_chat_agent_deployment.md)

## Running the Service
```bash
python3 main.py
```

