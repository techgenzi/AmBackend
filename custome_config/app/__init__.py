from flask import Flask, current_app
# from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from flask_restx import Api
from ipss_utils.ipss_db import IpssDb
from ipss_utils.ipss_api_doc import authorization_api_doc
import os
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from flask_redis import Redis
from ipss_utils.redis.ipss_redis import IpssRedis

db_client = SQLAlchemy()
db_cache = Cache()
rest_api = Api(
    title="CUSTOM_CONFIG API",
    doc="/custome_config/api-docs",
    authorizations=authorization_api_doc,
    security='api_key',
    base_url="/custome_config",
    url_scheme="http"
)
redis = Redis()
ipss_redis = IpssRedis()
ipss_db = IpssDb()

def create_app(config):
    app = Flask(__name__)
    # CORS(app)
    app.config.from_object(config)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db_client.init_app(app)
    db_cache.init_app(app)
    rest_api.init_app(app)
    ipss_db.init_app(app, db_client)
    redis.init_app(app)
    ipss_redis.init_app(app, redis)

    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        integrations=[FlaskIntegration()]
    )

    with app.app_context():
        from .api.tenant_config import custom_config_api_route
        rest_api.add_namespace(custom_config_api_route)
        
        if not current_app.config.get('IS_WORKER'):
            print("IT IS CALLED")
            ipss_redis.load_module()
        else:
            print("IT IS NOT CALLED")
            
        return app
