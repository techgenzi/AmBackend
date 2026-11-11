from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from flask_restx import Api
from ipss_utils.ipss_db import IpssDb
from ipss_utils.ipss_api_doc import authorization_api_doc
# import os

from flask_redis import Redis
from ipss_utils.redis.ipss_redis import IpssRedis

# import sentry_sdk
# from sentry_sdk.integrations.flask import FlaskIntegration

db_client = SQLAlchemy()
db_cache = Cache()
rest_api = Api(
    title="OrderSReports",
    doc="/order-reports/api-docs",
    authorizations=authorization_api_doc,
    security='api_key',
    base_url="/am-order-reports",
    url_scheme="http"
)
redis = Redis()
ipss_redis = IpssRedis()
ipss_db = IpssDb()


def create_app(config):
    app = Flask(
        __name__
    )
    app.config.from_object(config)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db_client.init_app(app)
    db_cache.init_app(app)
    # Registering routes
    rest_api.init_app(app)
    ipss_db.init_app(app, db_client)
    redis.init_app(app)
    ipss_redis.init_app(app, redis)

    with app.app_context():
        from .api.rm_purchase import orderReportsAPIRoutes
        rest_api.add_namespace(orderReportsAPIRoutes)
        if not current_app.config.get('IS_WORKER'):
            ipss_redis.load_module()
        return app
