import os
from datetime import timedelta


class Config:
    # SERVER_NAME = "127.0.0.1:5000"
    CACHE_TYPE = "redis"
    CACHE_REDIS_HOST = "redis"
    CACHE_REDIS_PORT = 6379
    CACHE_REDIS_DB = 0
    CACHE_REDIS_URL = os.getenv("REDIS_DB_URL", "redis://localhost:6379/0")
    CACHE_DEFAULT_TIMEOUT = 500
    # SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL", "postgresql+psycopg2://ipssvtmapi:AT4RuiqHUY098Alt3840lkfj@142.93.217.244:5438/vtmdb")
    # SQLALCHEMY_DATABASE_URI = os.getenv("COMPLIANCE_APP_DB",'''''')
    SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL",
                                        "")
    # SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL","")
    #SQLALCHEMY_DATABASE_URI ="postgresql://neo:esd@localhost:5432/urmanage"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True
    }
    SQLALCHEMY_ECHO = True
    IS_WORKER = False
    IPSS_PERMISSIONS = [
        {
            'module_name': "Production Stages",
            'module_group': "Production",
            'module_id': "product_stages_mapping",
            'module_description': "Here you can create Stages",

            'project_id': "pg-bluemetals",
            'permissions': ['list', 'view', 'add', 'edit', 'delete']
        }
    ]
