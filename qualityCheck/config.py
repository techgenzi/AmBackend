import os
from datetime import timedelta


class Config:
    # SERVER_NAME = "127.0.0.1:5005"
    CACHE_TYPE = "redis"
    CACHE_REDIS_HOST = "redis"
    CACHE_REDIS_PORT = 6379
    CACHE_REDIS_DB = 0
    CACHE_REDIS_URL = os.getenv("REDIS_DB_URL", "redis://localhost:6379/0")
    # CACHE_REDIS_URL = REDIS_URL = os.getenv("DB_URL",
    #                                         "redis://default:TkePeHiNKjXvB0gR9bq2eS3ZdohkqDVQ@redis-13570.c83.us-east-1-2.ec2.cloud.redislabs.com:13570")
    CACHE_DEFAULT_TIMEOUT = 500
    # SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL",
    #                                     "postgresql+psycopg2://ipss:66bAQRfNcFU3qMBe@139.59.83.9:5434/ipss_db")
    SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL",
                                        "postgresql+psycopg2://ipss:MBeQ66bqRfNAcFU3@139.59.83.9:5434/ipss_db")
    # SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL",
    #                                     "")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True
    }
    SQLALCHEMY_ECHO = True
    IS_WORKER = False
    IPSS_PERMISSIONS = [{
        'module_name': "Goods Received Notes",
        'module_group': "Goods Received Notes",
        'module_id': "quality_check",
        'project_id': "AM",
        'module_description': "Check the qualtiy of the products",
        'permissions': ['list', 'view', 'add', 'edit', 'delete']
    }
    ]
