import os
from datetime import timedelta


class Config:
    # SERVER_NAME = "127.0.0.1:5000"
    CACHE_TYPE = "redis"
    CACHE_REDIS_HOST = "redis"
    CACHE_REDIS_PORT = 6379
    CACHE_REDIS_DB = 0
    CACHE_REDIS_URL = REDIS_URL = os.getenv("REDIS_DB_URL", "redis://localhost:6379/0")
    CACHE_DEFAULT_TIMEOUT = 500
    SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL",
                                        "postgresql+psycopg2://ipss:MBeQ66bqRfNAcFU3@139.59.83.9:5434/ipss_db")
    # SQLALCHEMY_DATABASE_URI = os.getenv("USERS_DB_URL",
    # "postgresql+psycopg2://ipssapi:AT4RuiqHUY09840lkfjAlt38@64.227.180.3:5438/crmdb")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True
    }
    SQLALCHEMY_ECHO = False
    IS_WORKER = False
    IPSS_PERMISSIONS = [{
        'module_name': "APK Upload",
        'module_group': "APK",
        'module_id': "apk_id",
        'module_description': "Here you can access and download the latest mobile application apk",
        'project_id': "APK-Modules",
        'permissions': ['list', 'view', 'add', 'edit', 'delete', 'download']
    }]
