from flask import Flask, current_app, request

from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from flask_restx import Api
from ipss_utils.ipss_db import IpssDb
from ipss_utils.ipss_api_doc import authorization_api_doc
from flask_redis import Redis
from ipss_utils.redis.ipss_redis import IpssRedis

from flask_jwt_extended import JWTManager

from flask_socketio import SocketIO



db_client = SQLAlchemy()
socketio = SocketIO()

db_cache = Cache()
rest_api = Api(
    title="Notification API",
    doc="/notification/api-docs",
    authorizations=authorization_api_doc,
    security='api_key',
    base_url="/notification",
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
        from .api.notification import notification_api_route
        rest_api.add_namespace(notification_api_route)
        from .api import socket_events
    return app
