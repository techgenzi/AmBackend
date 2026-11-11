import os
from datetime import timedelta


class Config:
    # SERVER_NAME = "127.0.0.1:5000"
    CACHE_TYPE = "redis"
    CACHE_REDIS_HOST = "redis"
    CACHE_REDIS_PORT = 6379
    CACHE_REDIS_DB = 0

    CACHE_REDIS_URL = REDIS_URL = os.getenv("REDIS_DB_URL", "redis://default:redispw@localhost:49153")

    REDIS_DECODE_RESPONSES = True
    CACHE_DEFAULT_TIMEOUT = 500
    # JWT_SECRET_KEY = "565678uoiujg9t5968453gfgr6565@243"
    # JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=30)
    # JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=2)
    # SQLALCHEMY_DATABASE_URI = os.getenv("USERS_DB_URL", "postgresql+psycopg2://ipssapi:AT4RuiqHUY09840lkfjAlt38@142.93.217.230:5439/ecomdb")
    # SQLALCHEMY_DATABASE_URI = os.getenv("USERS_DB_URL", "postgresql+psycopg2://dataapi:AT4RuiqHUY09840lkfjAlt38@localhost:5432/dataapi")  # LOCAL DOCKER
    # SQLALCHEMY_DATABASE_URI = os.getenv("USERS_DB_URL", "postgresql+psycopg2://ipssapi:AT4RuiqHUY09840lkfjAlt38@64.227.180.3:5438/crmdb")
    # SQLALCHEMY_DATABASE_URI = os.getenv("USERS_DB_URL", "postgresql+psycopg2://ipss:MBeQ66bqRfNAcFU3@139.59.83.9:5434/ipss_db")
    SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL",
                                        "postgresql+psycopg2://ipss:MBeQ66bqRfNAcFU3@139.59.83.9:5434/ipss_db")  #dev_db

    #am-stageing
    # SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL", "") 

    # SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL","")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True
    }
    SQLALCHEMY_ECHO = True
    IS_WORKER = False
    IPSS_PERMISSIONS = [{
            'module_name': "Rank Configuration",
            'module_group': "Rank Config",
            'module_id': "rankconfig_ns",
            'module_description': "Configure the Rank for the purpose of Approval",
            'project_id': "Construction Management",
            'permissions': ['list', 'view', 'add', 'edit', 'delete']
        }
]