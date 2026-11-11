from app import create_app, db_client
from config import Config
from flask import g, request
import os, time, uuid

app = create_app(Config)

try:
    from flask_cors import CORS
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True, allow_headers=["Content-Type", "Authorization", "compcode", "tenant_id", "X-Trace-Id", "Accept", "Origin"])
except Exception:
    pass

@app.before_request
def before_request():
    g.start_time = time.time()
    g.trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())

@app.after_request
def after_request(response):
    if hasattr(g, 'start_time'):
        duration = round((time.time() - g.start_time) * 1000, 2)
        response.headers["X-Response-Time-ms"] = str(duration)
    # Ensure CORS headers on all responses
    response.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", "*")
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, compcode, tenant_id, X-Trace-Id, Accept, Origin"
    return response

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5015))
    app.run(host="0.0.0.0", port=port, debug=False)
