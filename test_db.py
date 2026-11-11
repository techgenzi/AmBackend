import sys
sys.path.append('b:/Brahadeesh/Techgenzi/AM/BackEnd/production_plans')
from app import create_app, db_client
from config import Config
from sqlalchemy import text

app = create_app(Config)
app.app_context().push()
s = db_client.session

try:
    s.execute(text('UPDATE plan_targets SET deleted=true, deleted_at=NOW() WHERE production_plan_id=622 AND deleted IS NOT TRUE'))
    print("plan_targets success")
except Exception as e:
    print("Error in plan_targets:", e)

try:
    s.execute(text('UPDATE production_plan_products SET deleted=true, deleted_at=NOW() WHERE production_plan_id=622 AND deleted IS NOT TRUE'))
    print("production_plan_products success")
except Exception as e:
    print("Error in production_plan_products:", e)

s.commit()
