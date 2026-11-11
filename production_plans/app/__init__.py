import os

from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_caching import Cache
from flask_restx import Api
from flask_migrate import Migrate
from ipss_utils.ipss_db import IpssDb
from ipss_utils.redis.ipss_redis import IpssRedis
from ipss_utils.ipss_api_doc import authorization_api_doc
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from flask_redis import Redis

db_client = SQLAlchemy()
jwt_manager = JWTManager()
db_cache = Cache()
redis = Redis()
ipss_redis = IpssRedis()
rest_api = Api(
    title="PROD_PLANS API",
    doc="/prod_plans/api-docs",
    authorizations=authorization_api_doc,
    security='api_key',
    base_url="/am-prod_plans",
    url_scheme="http"
)
ipss_db = IpssDb()
migrate = Migrate()


def create_app(config):
    app = Flask(
        __name__
    )
    app.config.from_object(config)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db_client.init_app(app)
    migrate.init_app(app, db_client)
    jwt_manager.init_app(app)
    db_cache.init_app(app)
    # redis.init_app(app)
    # ipss_redis.init_app(app, redis)
    # Registering routes
    rest_api.init_app(app)
    ipss_db.init_app(app, db_client)

    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        integrations=[FlaskIntegration()]
    )

    with app.app_context():
        from .api.planning import prod_plan_api_route
        rest_api.add_namespace(prod_plan_api_route)
        if not current_app.config.get('IS_WORKER'):
            ipss_redis.load_module()
        return app
