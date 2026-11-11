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
    # SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL",
    #                                     "postgresql+psycopg2://ipssvtmapi:AT4RuiqHUY098Alt3840lkfj@142.93.217.244:5438/vtmdb")

    # SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL",
    #                                     "postgresql+psycopg2://ipss:MBeQ66bqRfNAcFU3@139.59.83.9:5434/ipss_db")
    #

    SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL",
                                        "") #omniplusLive

    # SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL","postgresql+psycopg2://ipss:66bAQRfNcFU3qMBe@139.59.83.9:5434/ipss_db")
    #SQLALCHEMY_DATABASE_URI ="postgresql://neo:esd@localhost:5432/urmanage"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True
    }
    SQLALCHEMY_ECHO = True
    IS_WORKER = False
    IPSS_PERMISSIONS = [
        {
            'module_name': "Floor_Configuration",
            'module_group': "Production Configuration",
            'module_id': "floor",
            'module_description': "Here you can add the floor data",
            'project_id': "AM",
            'permissions': ['list', 'view', 'add', 'edit', 'delete']
        },{
            'module_name': "Stage_Configuration",
            'module_group': "Production Configuration",
            'module_id': "stage",
            'module_description': "Here you can add the stage data",
            'project_id': "AM",
            'permissions': ['list', 'view', 'add', 'edit', 'delete']
        }
    ]
