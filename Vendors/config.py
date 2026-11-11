import os
from datetime import timedelta


class Config:
    # SERVER_NAME = "127.0.0.1:5000"
    CACHE_TYPE = "redis"
    CACHE_REDIS_HOST = "redis"
    CACHE_REDIS_PORT = 6379
    CACHE_REDIS_DB = 0
    CACHE_REDIS_URL = os.getenv("REDIS_DB_URL", "redis://localhost:6379/0")
    # CACHE_REDIS_URL = REDIS_URL = os.getenv("DB_URL",
    #                                         "redis://default:TkePeHiNKjXvB0gR9bq2eS3ZdohkqDVQ@redis-13570.c83.us-east-1-2.ec2.cloud.redislabs.com:13570")
    CACHE_DEFAULT_TIMEOUT = 500
    # SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL",
    #                                     "postgresql+psycopg2://ipss:MBeQ66bqRfNAcFU3@139.59.83.9:5434/ipss_db")
    SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL",
                                        "postgresql+psycopg2://ipss:MBeQ66bqRfNAcFU3@139.59.83.9:5434/ipss_db") #dev

    # SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL",
    #                                     "") #omniplusLive

    # SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL", "postgresql+psycopg2://ipss:AT4RuiqHUY09840lkfjAlt38@128.199.20.17:5432/ipss") #stageing

    # SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL",
    #                                     "")
    # SQLALCHEMY_DATABASE_URI = os.getenv("COMPLIANCE_APP_DB",
    #                                     "")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True
    }
    SQLALCHEMY_ECHO = True
    IS_WORKER = False
    IPSS_PERMISSIONS = [{
        'module_name': "Vendor List and Configuration ",
        'module_group': "Vendor / Customer",
        'module_id': "vendor",
        'project_id': "ipss_po",
        'module_description': "Typically admin will configure this data . Vendor can be configured only "
                              "here and this data will be flown throughout the system ",
        'permissions': ['list', 'view', 'add', 'edit', 'delete', 'import', 'export']
    }, {
        'module_name': "Customer List and Configuration ",
        'module_group': "Vendor / Customer",
        'module_id': "Customers",
        'project_id': "ipss_po",
        'module_description': "Typically admin will configure this data . Customer can be configured only "
                              "here and this data will be flown throughout the system ",
        'permissions': ['list', 'view', 'add', 'edit', 'delete', 'import', 'export']
    },
        {
            'module_name': "Own Company and Configuration ",
            'module_group': "Vendor / Customer",
            'module_id': "our_company",
            'project_id': "ipss_po",
            'module_description': "Typically admin will configure this data . Own company can be configured only "
                                  "here and this data will be flown throughout the system ",
            'permissions': ['list', 'view', 'add', 'edit', 'delete']
        }
    ]
