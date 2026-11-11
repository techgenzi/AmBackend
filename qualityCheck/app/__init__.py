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
    title="Quality Check API",
    doc="/qualityCheck/api-docs",
    authorizations=authorization_api_doc,
    security='api_key',
    base_url="/am-qualitycheck",
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
        from sqlalchemy import text
        try:
            with db_client.engine.connect() as conn:
                # 1. grnlineitems columns
                conn.execute(text("ALTER TABLE grnlineitems ADD COLUMN IF NOT EXISTS is_qc_done BOOLEAN DEFAULT FALSE;"))
                conn.execute(text("ALTER TABLE grnlineitems ADD COLUMN IF NOT EXISTS qc_status VARCHAR(50) DEFAULT 'PENDING';"))
                conn.execute(text("ALTER TABLE grnlineitems ADD COLUMN IF NOT EXISTS supplier_lot_no VARCHAR(100);"))
                conn.execute(text("ALTER TABLE grnlineitems ADD COLUMN IF NOT EXISTS non_damaged_quantity VARCHAR(50);"))

                # 2. grnotes columns
                conn.execute(text("ALTER TABLE grnotes ADD COLUMN IF NOT EXISTS is_qc_done BOOLEAN DEFAULT FALSE;"))

                # 3. rejected_material table
                conn.execute(text('''
                    CREATE TABLE IF NOT EXISTS rejected_material (
                        id BIGSERIAL PRIMARY KEY,
                        unique_id VARCHAR(50) UNIQUE,
                        grnotesid BIGINT,
                        grnlineid BIGINT,
                        product_id BIGINT,
                        rejected_quantity NUMERIC,
                        rejection_reason JSON,
                        rejection_remark TEXT,
                        image_attachment JSON,
                        action VARCHAR(100) DEFAULT 'Return to Store',
                        store_id BIGINT,
                        status VARCHAR(50) DEFAULT 'Pending',
                        compcode BIGINT,
                        created_on TIMESTAMP DEFAULT NOW(),
                        created_by VARCHAR(100)
                    );
                '''))

                # 4. grn_item_serials table
                conn.execute(text('''
                    CREATE TABLE IF NOT EXISTS grn_item_serials (
                        id BIGSERIAL PRIMARY KEY,
                        grnotesid BIGINT,
                        product_id BIGINT,
                        serial_number VARCHAR(100),
                        qc_readings JSON,
                        compcode BIGINT,
                        deleted BOOLEAN DEFAULT FALSE,
                        created_on TIMESTAMP DEFAULT NOW()
                    );
                '''))
        except Exception as e:
            app.logger.warning(f"Could not auto-migrate QC tables/columns: {e}")

        from .api.qc import qc_api_route
        rest_api.add_namespace(qc_api_route)
        if not current_app.config.get('IS_WORKER'):  # add
            ipss_redis.load_module()  # add
        return app
