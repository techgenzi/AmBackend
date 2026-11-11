import datetime
from decimal import Decimal

from ipss_utils.ipss_db import query_to_dict

from .errorhandling import map_sqlalchemy_error_to_http_status
from .. import db_client
from flask import request
from sqlalchemy import update, text, bindparam, NUMERIC, Integer,Boolean
from sqlalchemy.exc import SQLAlchemyError

from ..models.planning import FGLog, FGLogDetails


def add_cc(data=[],pkey='',p_value=''):
    compcode = request.args.get('current_user', {})
    cc = {"compcode": compcode.get('company_id'),
          "created_on": datetime.datetime.now()
          }
    data=[{**cc,**i,**{pkey:p_value}} for i in data]
    return data
def get_current_user():
    current_user = request.args.get('current_user', {})
    return current_user.get('username')
def update_record(model, condition, values):
        """
        :param model: Model to be updated
        :param condition: Where condition
        :param values: Values
        :return:
        """
        error = ""
        if hasattr(model, 'created_by') and hasattr(model, 'modified_by'):
            values["modified_by"] = get_current_user()

        # Add modified at
        if hasattr(model, 'modified_on'):
            values["modified_on"] = datetime.datetime.now()

        try:
            stmt = (
                update(model)
                    .where(condition)
                    .values(**values)
            )
            result = db_client.session.execute(stmt)
            # db_client.session.commit()
        except SQLAlchemyError as e:
            error = str(e)
            print(error, 'error')
            return map_sqlalchemy_error_to_http_status(e)
        return {
            'success': True
        }
def updated_extract_order():
    return text('''
    UPDATE order_items_extract 
    SET quantity_planned = :plan_quantity
    WHERE extract_id = :order_extract_id 
    ''').bindparams(
            plan_quantity=bindparam('plan_quantity', type_=NUMERIC),
            order_extract_id=bindparam('order_extract_id', type_=Integer),
            # is_done=bindparam('is_done',type_=Boolean),
            # status=bindparam('status', type_=String)
        )


def remove_duplicates(dict_list):
    # Convert dictionaries to tuples of key-value pairs and use a set to remove duplicates
    seen = set()  # Set to keep track of seen frozensets
    unique_dicts = []  # List to store unique dictionaries

    for d in dict_list:
        # Convert dictionary items to a frozenset (unordered and hashable)
        dict_frozenset = frozenset(d.items())

        # If the frozenset is not in 'seen', it's a unique dictionary
        if dict_frozenset not in seen:
            unique_dicts.append(d)
            seen.add(dict_frozenset)  # Mark this frozenset as seen

    return unique_dicts


def update_fg_log(data, production_plan_id, s=db_client.session, commit=True):
    current_user = request.args.get('current_user', {})
    created_by = current_user.get('username')
    now = datetime.datetime.now(datetime.timezone.utc)
    compcode = current_user.get('company_id')
    try:
        # ------------------------------------------------
        # 1️⃣ INSERT FG LOG (MASTER)
        # ------------------------------------------------
        fg_log = FGLog(
            production_plan_id=production_plan_id,
            moved_quantity=data.get("moved_quantity"),
            cost_of_rawmaterial=Decimal(0),
            store_id = data.get("store_id"),
            compcode = compcode,
            created_on=now,
            created_by=created_by
        )
        s.add(fg_log)
        s.flush()

        log_id = fg_log.log_id

        query = text("""
              SELECT
                  bc.product_id,
                  bc.quantity,
                  mc.cost,
                  pp.planed_quantity
              FROM production_plan pp
              JOIN bom b
                  ON pp.product_id = b.product_id
              JOIN bom_component bc
                  ON b.bom_id = bc.bom_id
              LEFT JOIN material_cost mc
                  ON mc.product_id = bc.product_id
              WHERE pp.production_plan_id = :production_plan_id and b.deleted IS NOT TRUE AND bc.deleted IS NOT TRUE
          """)
        print(query)
        rows = s.execute(query, {"production_plan_id": production_plan_id})

        fg_log_details = []
        total_raw_material_cost = Decimal(0)
        moved_qty = Decimal(data.get("moved_quantity") or 0)

        for row in rows:
            component_qty = (
                Decimal(row.quantity)
                if row.quantity not in (None, "")
                else Decimal(0)
            )
            planed_qty = Decimal(row.planed_quantity or 1)
            cost_per_product = Decimal(row.cost or 0)

            # bc.quantity is the total required component quantity for the entire plan (planed_quantity).
            # Unit component qty = component_qty / planed_qty
            qty_per_unit = (component_qty / planed_qty) if planed_qty > 0 else Decimal(0)
            total_component_qty = qty_per_unit * moved_qty
            total_cost = total_component_qty * cost_per_product

            total_raw_material_cost += total_cost

            fg_log_details.append({
                "log_id": log_id,
                "product_id": row.product_id,
                "quantity": total_component_qty,
                "cost_per_product": cost_per_product,
                "total_cost": total_cost,
                "creted_on": now,
                "created_by": created_by
            })

        if fg_log_details:
            s.bulk_insert_mappings(FGLogDetails, fg_log_details)

        fg_log.cost_of_rawmaterial = total_raw_material_cost
        s.flush()

        if commit:
            s.commit()

    except Exception as e:
        s.rollback()
        print(e, "<<< Error in update_fg_log")
        return map_sqlalchemy_error_to_http_status(e)

    return {
        "success": True
    }


def get_labour_cost(s, production_plan_id):

    query = text(f'''
WITH base_data AS (
    SELECT
        el.emp_id,
        pp.production_plan_id,
        EXTRACT(EPOCH FROM (hc.hour_ends - hc.hour_starts)) / 3600
            AS worked_hours,
        hr.daily_wages,
        hr.ctc_amount,
        CASE
            WHEN hr.daily_wages = TRUE
                THEN hr.ctc_amount::numeric / 8.0
            ELSE
                hr.ctc_amount::numeric / (8.0 * 30)
        END AS hourly_rate
    FROM execution_log el
    JOIN plan_targets pt 
        ON pt.plan_target_id = el.target_id
    JOIN production_plan pp 
        ON pp.production_plan_id = pt.production_plan_id
    JOIN hour_config hc 
        ON hc.record_id = el.hour_config_id
    JOIN hremploymast hr 
        ON hr.hremploymastid = el.emp_id
    WHERE pp.production_plan_id =:production_plan_id
)
,
labour_cost_calc AS (
    SELECT
        production_plan_id,
        worked_hours::int,
        hourly_rate,
        (worked_hours * hourly_rate)::int AS labour_cost
    FROM base_data
),
plan_qty as (
select production_plan_id,moved_quantity from production_plan
where production_plan_id =:production_plan_id
)
SELECT
    pq.production_plan_id,
	pq.moved_quantity,
    SUM(lcc.labour_cost) AS total_labour_cost,
    ROUND(
        SUM(lcc.labour_cost) / NULLIF(pq.moved_quantity, 0),
        2
    ) AS labour_cost_per_product
FROM labour_cost_calc lcc
join plan_qty pq on pq.production_plan_id = lcc.production_plan_id
GROUP BY pq.production_plan_id,pq.moved_quantity
    ''')

    result = s.execute(query, {"production_plan_id": production_plan_id})
    row = result.fetchone()
    if row:
        return {
            "total_labour_cost": row.total_labour_cost or 0,
            "labour_cost_per_product": row.labour_cost_per_product or Decimal(0)
        }
    else:
        return {
            "total_labour_cost": 0,
            "labour_cost_per_product": Decimal(0)
        }


def get_material_cost(production_plan_id):

    query = text(f"""
        with allocated as (
            select prod_plan_id, product_id, sum(allocated_amount) as allocated_amount 
            from plan_allocation 
            where prod_plan_id =:production_plan_id and deleted is not true 
            group by prod_plan_id, product_id
        ),
        dispatched as(
            select inv.prod_plan_id,inv.product_id,sum(d.dispatch_amount) as dispatch_amount from invregistry inv
            join dispatch d on d.releseid = inv.releseid
            where inv.prod_plan_id =:production_plan_id
            group  by inv.product_id,inv.prod_plan_id
        ),
        returned as (
            select rm.prod_plan_id, rm.product_id,sum(rm.return_amount) as return_amount from return_material rm
            where rm.prod_plan_id =:production_plan_id and rm.status = 'Moved'
            group  by rm.prod_plan_id, rm.product_id
        ),
        consumed as(
            select 
                coalesce(a.prod_plan_id, d.prod_plan_id, r.prod_plan_id) as prod_plan_id,
                coalesce(a.product_id, d.product_id, r.product_id) as product_id,
                coalesce(a.allocated_amount, 0) as allocated_amount,
                coalesce(d.dispatch_amount, 0) as dispatch_amount,
                coalesce(r.return_amount, 0) as return_amount,
                (coalesce(a.allocated_amount, 0) + coalesce(d.dispatch_amount, 0) - coalesce(r.return_amount, 0)) as consumed 
            from allocated a
            full outer join dispatched d on a.prod_plan_id = d.prod_plan_id and a.product_id = d.product_id
            full outer join returned r on coalesce(a.prod_plan_id, d.prod_plan_id) = r.prod_plan_id and coalesce(a.product_id, d.product_id) = r.product_id
        )
        select c.prod_plan_id as production_plan_id, c.product_id, c.dispatch_amount, c.return_amount, c.consumed, (c.consumed*coalesce(mc.cost,0)) as total_cost 
        from consumed c
        left join material_cost mc on mc.product_id = c.product_id
    """)

    return query_to_dict(db_client.engine.execute(query, production_plan_id=production_plan_id))
