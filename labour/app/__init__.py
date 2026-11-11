
from flask import Flask,current_app
from flask_redis import Redis
from ipss_utils.redis.ipss_redis import IpssRedis
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from flask_restx import Api
from ipss_utils.ipss_db import IpssDb
from ipss_utils.ipss_api_doc import authorization_api_doc
from flask_pymongo import PyMongo
import os

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

db_client = SQLAlchemy()
db_cache = Cache()
rest_api = Api(
    title="Labour Cost API",
    doc="/labour/api-docs",
    authorizations=authorization_api_doc,
    security='api_key',
    base_url="/am-labour",
    url_scheme="http"
)
ipss_db = IpssDb()
redis = Redis()
ipss_redis = IpssRedis()

def create_app(config):
    app = Flask(
        __name__
    )

    app.config.from_object(config)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    redis.init_app(app)
    ipss_redis.init_app(app, redis)
    db_client.init_app(app)
    db_cache.init_app(app)
    # Registering routes
    rest_api.init_app(app)
    ipss_db.init_app(app, db_client)



    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        integrations=[FlaskIntegration()]
    )
    with app.app_context():
        try:
            from sqlalchemy import text
            with db_client.engine.begin() as conn:
                conn.execute(text("ALTER TABLE labour_cost ADD COLUMN IF NOT EXISTS rate_per_box NUMERIC;"))
                conn.execute(text("ALTER TABLE labour_cost_log ADD COLUMN IF NOT EXISTS rate_per_box NUMERIC;"))
        except Exception as e:
            print("Auto migration warning:", e)

        from .api.labour import labour_api_route
        rest_api.add_namespace(labour_api_route)
        if not current_app.config.get('IS_WORKER'):
            print("IT IS CALLED")
            ipss_redis.load_module()
        else:
            print("IT IS NOT CALLED")
        return app


