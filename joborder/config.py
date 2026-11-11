import os
from datetime import timedelta


class Config:
    #SERVER_NAME = "127.0.0.1:50030"
    CACHE_TYPE = "redis"
    CACHE_REDIS_HOST = "redis"
    CACHE_REDIS_PORT = 6379
    CACHE_REDIS_DB = 0
    CACHE_REDIS_URL = os.getenv("REDIS_DB_URL", "redis://localhost:6379/0")
    # CACHE_REDIS_URL = REDIS_URL = os.getenv("DB_URL",
    #                                         "redis://default:TkePeHiNKjXvB0gR9bq2eS3ZdohkqDVQ@redis-13570.c83.us-east-1-2.ec2.cloud.redislabs.com:13570")
    CACHE_DEFAULT_TIMEOUT = 500
    # SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL", "postgresql+psycopg2://ipss:MBeQ66bqRfNAcFU3@139.59.83.9:5434/ipss_db")
    # SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL",
    #                                     "postgresql+psycopg2://ipssapi:AT4RuiqHUY09840lkfjAlt38@128.199.30.20:5438/ecomdb")
    # SQLALCHEMY_DATABASE_URI = os.getenv("COMPLIANCE_APP_DB",
    #                                     "postgresql+psycopg2://ipssapi:CqIcqK7rrP7kf2wXXfSkxI35#GTuUPTR@142.93.217.230:5438/compliance_app")

    SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL",
                                        "postgresql+psycopg2://ipss:MBeQ66bqRfNAcFU3@139.59.83.9:5434/ipss_db")

    # SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL", "") #stageing

    # SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DB_URL",
    #                                     "")  ##omniplus-Live

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True
    }
    SQLALCHEMY_ECHO = True
    IS_WORKER = False
    IPSS_PERMISSIONS = [{
        'module_name': "Raise Purchase order",
        'module_group': "Purchase Order",
        'module_id': "purchaseOrder",
        'project_id': "ipss_po",
        'module_description': "Allows user to raise purchase order.Typically users who manage the purchase orders for "
                              "the company will have access to purcahse order",
        'permissions': ['list', 'view', 'add', 'edit', 'delete', 'import', 'export']
    },
        {
            'module_name': "Purchase Order Quotation",
            'module_group': "Purchase Order",
            'module_id': "POQuotation",
            'project_id': "ipss_po",
            'module_description': "To quote all items from the purchase order proposal.",
            'permissions': ['list', 'view', 'add', 'edit', 'delete', 'import', 'export']
        }
    ]
