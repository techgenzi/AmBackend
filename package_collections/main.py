

from app import create_app, db_client
from config import Config
# from flask_cors import CORS

app = create_app(Config)

# CORS(app)


from flask import g, request
import os, redis, uuid, time, json

def get_client_ip():
    # 1. Try X-Forwarded-For header (can contain multiple IPs)
    x_forwarded_for = request.headers.get('X-Forwarded-For')
    if x_forwarded_for:
        # The first IP is the actual client
        return x_forwarded_for.split(',')[0].strip()

    # 2. Try X-Real-IP header
    x_real_ip = request.headers.get('X-Real-IP')
    if x_real_ip:
        return x_real_ip

    # 3. Fallback to default remote address
    return request.remote_addr

REDIS_URL = os.getenv("REDIS_DB_URL", "redis://localhost:6379/0")

redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True
)

@app.before_request
def before_request():
    g.start_time = time.time()
    g.trace_id = request.headers.get("X-Trace-Id")

    if not g.trace_id:
        g.trace_id = str(uuid.uuid4())

    g.request_data = {
        "trace_id": g.trace_id,
        "method": request.method,
        "url": request.url,
        "query_params": request.args.to_dict(),
        "body": request.get_json(silent=True),
        # "ip": request.remote_addr
        "ip": get_client_ip()
    }


import datetime

def json_serializer(obj):
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    return str(obj)

@app.after_request
def after_request(response):
    log = {
        **g.request_data,
        "request": request.get_json(silent=True),
        "status_code": response.status_code,
        "duration_sec": round((time.time() - g.start_time), 2),
        'user_id': request.args.get('current_user', {}).get('userid', None)
    }

    resp = response.get_json(silent=True)

    if isinstance(resp, list):
        resp = resp[0]
    if resp:
        log["msg"] = (resp.get("error") or resp.get("message"))

    # print(log)

    redis_client.lpush("api_logs", json.dumps(log, default=json_serializer))

    return response

if __name__ == "__main__":
    app.run()
    # app.run(host='0.0.0.0',port=5024)