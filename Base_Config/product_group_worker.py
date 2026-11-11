import time
import redis
from app.redis_client.redis_client import redis_client
from app.api.helper import check_product_code_associated_to_product_group
from worker_db import SessionLocal
from app.models import *


def ensure_product_group(redis_client):
    try:
        redis_client.xgroup_create(
            name="product_group_sequence_update_stream",
            groupname="product-group-sequence-workers",
            id="0",
            mkstream=True
        )
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise


def product_group_sequence_worker():
    ensure_product_group(redis_client)
    db_client = SessionLocal()
    while True:
        events = redis_client.xreadgroup(
            groupname="product-group-sequence-workers",
            consumername="worker-1",
            streams={"product_group_sequence_update_stream": ">"},
            count=10,
            block=5000
        )
        if not events:
            time.sleep(1)
            continue
        for stream, messages in events:
            for msg_id, data in messages:
                product_group_id = data["product_group_id"]
                compcode = data.get('compcode')
                check_product_code_associated_to_product_group(product_group_id=product_group_id, s=db_client, compcode=compcode)
                redis_client.xack("product_group_sequence_update_stream", "product-group-sequence-workers", msg_id)


if __name__ == "__main__":
    print("Worker2 started...")
    product_group_sequence_worker()
