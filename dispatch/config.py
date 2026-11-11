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
    # SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL","postgresql+psycopg2://ipssvtmapi:AT4RuiqHUY098Alt3840lkfj@142.93.217.244:5438/vtmdb")
    # SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL",
    #                                     "postgresql+psycopg2://ipss:MBeQ66bqRfNAcFU3@139.59.83.9:5434/ipss_db")

    # SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL",'''postgresql+psycopg2://ipssapi:CqIcqK7rrP7kf2wXXfSkxI35#GTuUPTR@142.93.217.230:5438/compliance_app''')
    SQLALCHEMY_DATABASE_URI = os.getenv("",
                                        "postgresql+psycopg2://ipss:MBeQ66bqRfNAcFU3@139.59.83.9:5434/ipss_db")

    # SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL", "s") #stageing
    # SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL",
    #                                                 "") #stageing
    # SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL", "") #am-staging

    # SQLALCHEMY_DATABASE_URI ="postgresql://neo:esd@localhost:5432/urmanage"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True
    }

    SQLALCHEMY_ECHO = True
    IPSS_PERMISSIONS = [
        {
        'module_description': "Here you can manage Inventory actions and manual updations",
        'project_id': "AM",
        'module_name': "Manual Stock Addition",
        'module_group': "Goods Registry",
        'module_id': "dispatch",
        'permissions': ['list','add', 'import', 'export','revert']
    }
    ]



