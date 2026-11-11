from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from flask_restx import Api
from .api_doc import chat_agent_authorizations

db_client = SQLAlchemy()
db_cache = Cache()
rest_api = Api(
    title="AI CHAT AGENT API",
    doc="/chat_agent/api-docs",
    authorizations=chat_agent_authorizations,
    security='apikey',
    base_url="/fabrico/chatAgent",
    url_scheme="http"
)

def create_app(config):
    app = Flask(__name__)
    app.config.from_object(config)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db_client.init_app(app)
    db_cache.init_app(app)

    from .routes.chat_agent import chat_agent_api_route
    from .api import chat_agent
    rest_api.add_namespace(chat_agent_api_route)

    rest_api.init_app(app)
    return app
