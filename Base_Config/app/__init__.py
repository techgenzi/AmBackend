from flask import Flask,current_app
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
    title="PRODUCTS API",
    doc="/products/api-docs",
    authorizations=authorization_api_doc,
    security='api_key',
    base_url="/baseConfig",
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

    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        integrations=[FlaskIntegration()]
    )

    with app.app_context():

        from .api.products import products_api_route
        rest_api.add_namespace(products_api_route)
        from .api.product_group import product_group_api_route
        rest_api.add_namespace(product_group_api_route)
        from .api.variant_attribute import variant_attribute_api_route
        rest_api.add_namespace(variant_attribute_api_route)
        from .api.variant_value import variant_value_api_route
        rest_api.add_namespace(variant_value_api_route)
        from .api.product_attribute import product_attribute_api_route
        rest_api.add_namespace(product_attribute_api_route)
        from .api.product_group_attributes_group import product_group_attributes_group_api_route
        rest_api.add_namespace(product_group_attributes_group_api_route)
        from .api.uom import uom_api_route
        rest_api.add_namespace(uom_api_route)
        from .api.line_config import line_config_api_route
        rest_api.add_namespace(line_config_api_route)
        from .api.hour_config import line_config_api_route
        rest_api.add_namespace(line_config_api_route)
        from .api.process_config import process_api_route
        rest_api.add_namespace(process_api_route)

        from .api.category import category_api_route
        rest_api.add_namespace(category_api_route)
        from .api.style import style_api_route
        rest_api.add_namespace(style_api_route)
        from .api.category import style_category_api_route
        rest_api.add_namespace(style_category_api_route)
        from .api.style import style_product_api_route
        rest_api.add_namespace(style_product_api_route)

        if not current_app.config.get('IS_WORKER'):
            print("IT IS CALLED")
            ipss_redis.load_module()
        else:
            print("IT IS NOT CALLED")
        return app
