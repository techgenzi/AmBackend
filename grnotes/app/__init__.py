from flask import Flask, current_app
from flask_redis import Redis
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from flask_restx import Api
from ipss_utils.ipss_db import IpssDb
from ipss_utils.ipss_api_doc import authorization_api_doc
import os
import sentry_sdk
from ipss_utils.redis.ipss_redis import IpssRedis
from sentry_sdk.integrations.flask import FlaskIntegration

db_client = SQLAlchemy()
db_cache = Cache()
redis = Redis()
ipss_redis = IpssRedis()

rest_api = Api(
    title="GRNotes API",
    doc="/grnotes/api-docs",
    authorizations=authorization_api_doc,
    security='api_key',
    base_url="/am-grnotes",
    url_scheme="http"
)
ipss_db = IpssDb()


def create_app(config):
    app = Flask(
        __name__
    )
    app.config.from_object(config)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db_client.init_app(app)
    db_cache.init_app(app)
    redis.init_app(app)  # add
    ipss_redis.init_app(app, redis)  # add
    # Registering routes
    rest_api.init_app(app)
    ipss_db.init_app(app, db_client)

    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        integrations=[FlaskIntegration()]
    )

    with app.app_context():
        # Register route blueprints
        # from .api import user_routes
        # app.register_blueprint(user_routes)
        from .api.grnotes import grnotes_api_route
        rest_api.add_namespace(grnotes_api_route)
        from .api.reports import grnotes_api_route
        rest_api.add_namespace(grnotes_api_route)
        if not current_app.config.get('IS_WORKER'):  # add
            ipss_redis.load_module()  # add
        return app
