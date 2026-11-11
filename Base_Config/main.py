from app import create_app, db_client
from config import Config

app = create_app(Config)


# from flask_cors import CORS
# CORS(app)


from flask import g, request
import os, redis, uuid, time, json
import datetime
from sqlalchemy import text

# Defensive import for APScheduler so environments without the package do not crash
try:
    from flask_apscheduler import APScheduler
    scheduler = APScheduler()
    has_scheduler = True
except ImportError as e:
    scheduler = None
    has_scheduler = False
    print(f"[Base_Config] Warning: Flask-APScheduler not installed ({e}). Background refresh job is disabled.")

# Track in-memory refresh job execution state
mv_refresh_tracker = {
    "last_attempt_time": None,
    "last_success_time": None,
    "last_error": None,
    "last_duration_seconds": None,
    "execution_count": 0,
    "scheduler_active": has_scheduler
}

def refresh_materialized_view():
    from app import db_client
    start_ts = time.time()
    mv_refresh_tracker["last_attempt_time"] = datetime.datetime.utcnow().isoformat() + "Z"
    mv_refresh_tracker["execution_count"] += 1
    try:
        db_client.session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_manufacturing_fact;"))
        db_client.session.commit()
        mv_refresh_tracker["last_success_time"] = datetime.datetime.utcnow().isoformat() + "Z"
        mv_refresh_tracker["last_duration_seconds"] = round(time.time() - start_ts, 2)
        mv_refresh_tracker["last_error"] = None
    except Exception as e:
        err_msg = str(e)
        print(f"Failed to refresh mv_daily_manufacturing_fact: {err_msg}")
        mv_refresh_tracker["last_error"] = err_msg
        db_client.session.rollback()

if has_scheduler and scheduler:
    try:
        scheduler.add_job(id='refresh_mv', func=refresh_materialized_view, trigger='interval', minutes=15)
        scheduler.start()
    except Exception as e:
        print(f"[Base_Config] Scheduler initialization error: {e}")

@app.route('/baseConfig/mv_status', methods=['GET'])
def get_mv_status():
    from app import db_client
    try:
        # 1. Fetch PostgreSQL Engine Stats
        pg_stats_query = text("""
            SELECT 
                s.relname,
                s.last_vacuum,
                s.last_autovacuum,
                s.last_analyze,
                s.last_autoanalyze,
                s.n_live_tup,
                s.n_dead_tup,
                pg_size_pretty(pg_total_relation_size(c.oid)) as total_size,
                c.relispopulated as is_populated
            FROM pg_stat_user_tables s
            JOIN pg_class c ON c.relname = s.relname
            WHERE s.relname = 'mv_daily_manufacturing_fact';
        """)
        row = db_client.engine.execute(pg_stats_query).fetchone()
        
        if not row:
            return {
                "status": "NOT_FOUND",
                "message": "Materialized view mv_daily_manufacturing_fact does not exist"
            }, 404

        # 2. Fetch Aggregation Summary (Date coverage & rows)
        summary_query = text("""
            SELECT 
                MIN(execution_date) as earliest_date,
                MAX(execution_date) as latest_date,
                COUNT(DISTINCT execution_date) as total_days_covered,
                COUNT(*) as total_rows
            FROM mv_daily_manufacturing_fact;
        """)
        summary_row = db_client.engine.execute(summary_query).fetchone()

        return {
            "status": "HEALTHY" if mv_refresh_tracker["last_error"] is None else "DEGRADED",
            "materialized_view": {
                "name": row[0],
                "is_populated": row[8],
                "disk_size": row[7],
                "live_tuples": row[5],
                "dead_tuples": row[6],
                "earliest_execution_date": str(summary_row[0]) if summary_row and summary_row[0] else None,
                "latest_execution_date": str(summary_row[1]) if summary_row and summary_row[1] else None,
                "last_refresh_timestamp": mv_refresh_tracker.get("last_success_time") or str(row[2]) or str(row[4]) or None,
                "total_days_recorded": summary_row[2] if summary_row else 0,
                "total_records": summary_row[3] if summary_row else 0
            },
            "postgres_maintenance_timestamps": {
                "last_vacuum": str(row[1]) if row[1] else None,
                "last_autovacuum": str(row[2]) if row[2] else None,
                "last_analyze": str(row[3]) if row[3] else None,
                "last_autoanalyze": str(row[4]) if row[4] else None
            },
            "scheduler_job_telemetry": {
                "job_id": "refresh_mv",
                "trigger_interval": "15 minutes",
                "execution_count": mv_refresh_tracker["execution_count"],
                "last_attempt_time": mv_refresh_tracker["last_attempt_time"],
                "last_success_time": mv_refresh_tracker["last_success_time"],
                "last_duration_seconds": mv_refresh_tracker["last_duration_seconds"],
                "last_error": mv_refresh_tracker["last_error"]
            }
        }, 200
    except Exception as e:
        return {
            "status": "ERROR",
            "message": str(e)
        }, 500

@app.route('/baseConfig/refresh_mv', methods=['POST'])
def trigger_refresh_mv():
    """Manual on-demand trigger to refresh the manufacturing fact materialized view."""
    try:
        refresh_materialized_view()
        if mv_refresh_tracker["last_error"]:
            return {
                "success": False,
                "message": f"Refresh failed: {mv_refresh_tracker['last_error']}",
                "telemetry": mv_refresh_tracker
            }, 500
        return {
            "success": True,
            "message": "Materialized view mv_daily_manufacturing_fact refreshed successfully",
            "telemetry": mv_refresh_tracker
        }, 200
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }, 500

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
    # app.run(host='0.0.0.0',port=5003)