import datetime
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from .errorhandling import map_sqlalchemy_error_to_http_status
from ..models.prod_stages import ProdStages, ActivityStageMap
from flask import request
from .. import db_client


def transform(data):
    """Attach stage_id to each activity."""
    for stage in data.get('stages', []):
        for activity in stage.get('activities', []):
            activity['stage_id'] = stage.get('stage_id')
    return data


def post_query():
    data = transform(request.json)

    product_id = data.pop('product_id', None)
    compcode = request.args.get('current_user', {}).get('company_id')

    cc = {"compcode": compcode, "created_on": datetime.datetime.now()}

    success, error = False, ''
    activities, updateData, upActivities = [], [], []

    # Extract stages and activities
    items = [{**i, **cc, "product_id": product_id} for i in data.pop('stages', [])]
    # activities = [a for stage in items for a in stage.pop('activities', [])]
    activities = [j for i in items for j in i.get('activities', [])]
    # Split into inserts & updates
    updateData = [items.pop(i) for i in range(len(items) - 1, -1, -1) if 'id' in items[i]]
    upActivities = [activities.pop(i) for i in range(len(activities) - 1, -1, -1) if
                    'activity_stage_map_id' in activities[i]]

    s = db_client.session
    try:
        # Bulk insert/update stages
        if items:
            s.bulk_insert_mappings(ProdStages, items)
        if updateData:
            s.bulk_update_mappings(ProdStages, updateData)
        s.commit()
        if activities or not activities:
            # Fetch stage mappings
            stage_query = text('''
                SELECT s.stage_id, ps.id AS production_stage_id
                FROM stage s
                JOIN production_stages ps ON ps.stage_id = s.stage_id
                WHERE s.deleted = FALSE AND ps.deleted = FALSE AND ps.product_id = :product_id
            ''')
            stage_map = {row.stage_id: row.production_stage_id for row in
                         s.execute(stage_query, {"product_id": product_id}).fetchall()}

            # Assign production_stage_id to activities
            for activity in activities:
                if activity["stage_id"] in stage_map:
                    activity["production_stage_id"] = stage_map[activity["stage_id"]]
                    activity.update(cc)

            # Bulk insert/update activities
            if activities:
                s.bulk_insert_mappings(ActivityStageMap, activities)
            if upActivities:
                s.bulk_update_mappings(ActivityStageMap, upActivities)
            s.commit()

        success = True
        message = "Records created successfully"

    except SQLAlchemyError as e:
        s.rollback()
        return map_sqlalchemy_error_to_http_status(e)

    return {"success": success, "message": message, "error": error}
