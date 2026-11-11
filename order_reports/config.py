import os
from datetime import timedelta


class Config:
    CACHE_TYPE = "redis"
    CACHE_REDIS_HOST = "redis"
    CACHE_REDIS_PORT = 6379
    CACHE_REDIS_DB = 0
    CACHE_REDIS_URL = os.getenv("REDIS_DB_URL", "redis://localhost:6379/0")
    CACHE_DEFAULT_TIMEOUT = 500
    SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL",
                                        "postgresql+psycopg2://ipss:MBeQ66bqRfNAcFU3@139.59.83.9:5434/ipss_db")
    
    # SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL", "") #stageing
    # SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL",
    #                                     "postgresql+psycopg2://ipssvtmapi:AT4RuiqHUY098Alt3840lkfj@142.93.217.244:5438/vtmdb")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True
    }
    SQLALCHEMY_ECHO = True
    IS_WORKER = False
    IPSS_PERMISSIONS = [{
        'module_name': "Grade Configuration",
        'module_group': "Product Configuration",
        'module_id': "grade",
        'module_description': "Here you can Alter/Add Prodcut Group "
                              "This type of permission is usually for admins only.",
        'project_id': "Inventory",
        'permissions': ['list', 'view', 'add', 'edit', 'delete']
    }
    ]
