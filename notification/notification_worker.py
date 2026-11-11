import time
import redis

from app.redis_client.redis_client import redis_client
from worker_db import SessionLocal

from app.api.helper import production_plan_creation, execution_qty_exceeded_notification


STREAM_NAME = "notification"
GROUP_NAME = "notification-workers"
CONSUMER_NAME = "worker-1"


def ensure_notification_group():

    try:

        redis_client.xgroup_create(
            name=STREAM_NAME,
            groupname=GROUP_NAME,
            id="0",
            mkstream=True
        )

    except redis.exceptions.ResponseError as e:

        if "BUSYGROUP" not in str(e):
            raise


def notification_worker():

    ensure_notification_group()

    while True:

        try:

            events = redis_client.xreadgroup(
                groupname=GROUP_NAME,
                consumername=CONSUMER_NAME,
                streams={STREAM_NAME: ">"},
                count=10,
                block=5000
            )

            if not events:
                continue

            for stream, messages in events:

                for msg_id, data in messages:
                    db_client = SessionLocal()

                    try:

                        action = data.get("action")

                        # Only production plan creation
                        if action == "production_plan_creation":

                            production_plan_id = data.get("production_plan_id")
                            plan_unique = data.get("plan_unique")
                            company_id = data.get("company_id")
                            username = data.get("username")
                            production_plan_creation(production_plan_id,plan_unique,company_id,db_client,username)
                        
                        elif action == "execution_qty_exceeded":
                            company_id = data.get("company_id")
                            execution_qty_exceeded_notification(data, company_id, db_client)

                        db_client.commit()

                        redis_client.xack(
                            STREAM_NAME,
                            GROUP_NAME,
                            msg_id
                        )

                    except Exception as inner_error:

                        db_client.rollback()

                        print(
                            f"Message Processing Error: "
                            f"{inner_error}"
                        )
                    finally:
                        db_client.close()

        except Exception as outer_error:

            print(f"Worker Error: {outer_error}")

            time.sleep(5)


if __name__ == "__main__":

    print("Notification Worker Started...")

    notification_worker()