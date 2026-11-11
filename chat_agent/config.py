import os
from datetime import timedelta

class Config:
    CACHE_TYPE = "redis"
    CACHE_REDIS_HOST = "redis"
    CACHE_REDIS_PORT = 6379
    CACHE_REDIS_DB = 0
    CACHE_REDIS_URL = os.getenv("REDIS_DB_URL", "redis://localhost:6379/0")
    CACHE_DEFAULT_TIMEOUT = 500

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "PROD_DB_URL",
        os.getenv("HRCOMMON_DB_URL", "postgresql+psycopg2://ipss:MBeQ66bqRfNAcFU3@139.59.83.9:5434/ipss_db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True
    }
    SQLALCHEMY_ECHO = False
    IS_WORKER = False

    # Base ERP Gateway URL for internal/external GET APIs
    BASE_URL = os.getenv("BASE_URL", "https://ipssapi.techgenzi.com").rstrip('/')

    # LLM & AI Chat Configuration (Ollama Cloud / OpenAI Compatible Endpoint)
    LLM_API_URL = os.getenv("LLM_API_URL", "https://api.ollama.com/api/chat").strip()
    LLM_API_KEY = os.getenv("LLM_API_KEY", "26d01b0e81b44a9497419bc173472808.wc5rzRfUZ6qxS712XNmskvxX").strip()
    LLM_MODEL = os.getenv("LLM_MODEL", "gemma4:31b").strip()
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "Google / Gemma").strip()
    LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "120"))

    # Large JSON Response Controls (Optimized for Quantized LLM context)
    MAX_TOOL_RESPONSE_ITEMS = int(os.getenv("MAX_TOOL_RESPONSE_ITEMS", "15"))
    MAX_TOOL_RESPONSE_CHARS = int(os.getenv("MAX_TOOL_RESPONSE_CHARS", "6000"))

    IPSS_PERMISSIONS = [{
        'module_name': "Chat Agent",
        'module_group': "AI Features",
        'module_id': "chat_agent",
        'module_description': "AI Sync Chat with Tool Calling across AmNonOvens and Fabrico360 ERP GET APIs",
        'project_id': "fabrico360",
        'permissions': ['chat', 'view']
    }]
