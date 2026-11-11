import os


class Config:
    CACHE_TYPE = "redis"
    CACHE_REDIS_HOST = "redis"
    CACHE_REDIS_PORT = 6379
    CACHE_REDIS_DB = 0
    CACHE_REDIS_URL = os.getenv("REDIS_DB_URL", "redis://localhost:6379/0")
    CACHE_DEFAULT_TIMEOUT = 500

    # PostgreSQL Database URL
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "PROD_DB_URL",
        "postgresql+psycopg2://ipss:MBeQ66bqRfNAcFU3@139.59.83.9:5434/ipss_db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True
    }
    SQLALCHEMY_ECHO = True
    IS_WORKER = False

    # புதிய Custom Config Module-க்கான அனுமதிகள் (Permissions)
    IPSS_PERMISSIONS = [
        {
            'module_name': "Custom_Config",
            'module_group': "Custom Configuration",
            'module_id': "custom-config",
            'module_description': "Here you can manage custom configurations",
            'project_id': "AM",
            'permissions': ['list', 'view', 'add', 'edit', 'delete']
        }
    ]
