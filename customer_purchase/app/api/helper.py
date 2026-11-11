import datetime
import json
from os import abort

from ..api.errorhandling import map_sqlalchemy_error_to_http_status
from flask import request
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, bindparam, NUMERIC, Integer, String, insert, BigInteger
from sqlalchemy.sql.coercions import expect
from ..model.customer_purchase import OrderExtarct
from .. import db_client
from .errorhandling import get_current_user
from decimal import Decimal


def insert_record(model, values, commit=True):
    """
    Insert record helper utility
    :param model: Model to be inserted
    :param values: Model values
    :return: Success with inserted id or error message
    """
    current_user = request.args.get('current_user')
    primary_key_id = None
    # Add current users to the record
    if hasattr(model, 'created_by') and hasattr(model, 'modified_by'):
        values["created_by"] = get_current_user()
        values["modified_by"] = get_current_user()

    # Add created at and modified at
    if hasattr(model, 'created_on'):
        values["created_on"] = datetime.datetime.now()
    if hasattr(model, 'modified_on'):
        values["modified_on"] = datetime.datetime.now()

    if hasattr(model, "compcode"):
        col_compcode = model.__table__.columns["compcode"]
        if isinstance(col_compcode.type, BigInteger):
            # Filter by company code
            values['compcode'] = current_user.get('company_id')

    if hasattr(model, 'finyear'):
        finyear_col = model.__table__.columns["finyear"]
        if isinstance(finyear_col.type, BigInteger):
            values['finyear'] = current_user.get('finyr_id')

    if hasattr(model, "tcompcode"):
        col_compcode = model.__table__.columns["tcompcode"]
        if isinstance(col_compcode.type, BigInteger):
            # Filter by company code
            values['tcompcode'] = current_user.get('company_id')

    if hasattr(model, 'tfinyear'):
        finyear_col = model.__table__.columns["tfinyear"]
        if isinstance(finyear_col.type, BigInteger):
            values['tfinyear'] = current_user.get('finyr_id')

    error = ""
    try:
        stmt = (
            insert(model)
            .values(**values)
        )
        result = db_client.session.execute(stmt)
        if commit:
            db_client.session.commit()
        primary_key_id = result.inserted_primary_key
    except Exception as e:
        from .errorhandling import map_sqlalchemy_error_to_http_status
        return map_sqlalchemy_error_to_http_status(e)
        error = str(e)
        db_client.session.flush()
    return {
        'success': True if primary_key_id else False,
        'error': error,
        'primary_key_id': primary_key_id
    }

def data_extract_from_package(customer_purchase_id=0):
    sql_query=text('''
    select coalesce(p2.product_id,p.product_id) product_id,items_id as order_items_id,
    (coalesce(pc.needded_count,1)::numeric * quantity_ordered)::text as quantity_ordered
    from customer_purchase_items p 
    left join package_items pc on pc.pakage_id =p.product_id and pc.deleted is not true and pc.is_package_material is not true
    left join products p2 on p2.product_id =pc.product_id and p2.deleted is not true
    where p.deleted is not true and p.customer_purchase_id=:customer_purchase_id
    union 
    select cpi.product_id,items_id as order_items_id ,
    cpi.quantity_ordered::text from customer_purchase_items cpi 
    where cpi.deleted is not true and cpi.customer_purchase_id =:customer_purchase_id
    ''')
    sql_query=query_to_dict(db_client.engine.execute(sql_query,customer_purchase_id=customer_purchase_id))
    return sql_query
def bulk_validate(data=[],table_name=''):
    # if len(data):
    data=json.dumps(data)
    check_d = text(f'''
                   SELECT json_agg(data.*) as data
                       FROM json_array_elements(:datas) AS data
                       left JOIN {table_name} tm
                           ON data->>'order_items_id' = tm.order_items_id::text and tm.deleted is not true
                           and data->>'product_id' = tm.product_id::text
                           where tm.extract_id is null  
                   ''')
    check_d = query_to_dict(db_client.engine.execute(check_d,datas=data))
    return check_d[0].get('data',[]) if len(check_d) and check_d[0].get('data') else []
def upadte_return(data=[],table_name=''):
    data = json.dumps(data)
    check_d = text(f'''
                       SELECT json_agg(data) as data
                           FROM json_array_elements(:datas) AS data
                           left JOIN {table_name} tm
                               ON data->>'order_items_id' = tm.order_items_id::text and tm.deleted is not true
                               and data->>'product_id' = tm.product_id::text
                               where tm.extract_id is not null  
                       ''')
    check_d = query_to_dict(db_client.engine.execute(check_d, datas=data))
    return check_d[0].get('data',[]) if len(check_d) and check_d[0].get('data') else []

def updated_order_items_extract():

    return text('''
    update order_items_extract set quantity_ordered=:quantity_ordered
    where product_id=:product_id and order_items_id=:order_items_id
    ''').bindparams(
            quantity_ordered=bindparam('quantity_ordered', type_=NUMERIC),
            product_id=bindparam('product_id', type_=Integer),
            order_items_id=bindparam('order_items_id',type_=Integer)
        )

def order_extract(data=[]):
    updata=upadte_return(data=data,table_name='order_items_extract')
    postdata=bulk_validate(data=data,table_name='order_items_extract')
    compcode = request.args.get('current_user', {})
    cc = {"compcode": compcode.get('company_id'),
          "created_on": datetime.datetime.now(),
          }
    postdata=[{**cc,**i} for i in postdata]
    # with db_client.session.begin():
    # db_client.session.close()
    if updata:
        db_client.session.execute(updated_order_items_extract(),updata)
    if postdata:
        db_client.session.bulk_insert_mappings(mapper=OrderExtarct,mappings=postdata)
    db_client.session.commit()

def get_labour_cost(s, production_plan_id):
    query = text(f"""
    SELECT
        pt.production_plan_id,
        COALESCE(SUM(el.labour_cost), 0) AS total_labour_cost,
        COALESCE(SUM(el.labour_cost) / NULLIF((SELECT moved_quantity FROM production_plan WHERE production_plan_id = pt.production_plan_id LIMIT 1), 0), 0) AS labour_cost_per_product
    FROM execution_log el
    JOIN plan_targets pt ON pt.plan_target_id = el.target_id
    WHERE pt.production_plan_id = :production_plan_id AND el.deleted IS NOT TRUE
    GROUP BY pt.production_plan_id
    """)
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

def get_estimated_labour_cost(s, production_plan_id, compcode):
    query = text(f"""
        with final_stage as(
            select ps.product_id, ps.stage_id, asm.config_id
            from production_stages ps
            join activity_stage_map asm on asm.production_stage_id = ps.id and asm.is_final_process is true
            where ps.compcode=:compcode and ps.deleted is not true and asm.deleted is not true
        ),
        estimated_cost as (
            SELECT 
                lc.product_id,
                (elem->>'stage_id')::int AS stage_id,
                sum((elem->>'rate')::numeric) AS rate
            FROM labour_cost lc
            CROSS JOIN LATERAL json_array_elements(COALESCE(lc.add_attribute::json, '[]'::json)) AS elem
            where lc.compcode = :compcode and lc.deleted is not true
            group by lc.product_id, stage_id
        ),
        stage_qty as (
            select pp.production_plan_id, pp.product_id, el.stage_id, sum(el.outward_qty) as outward_qty
            from production_plan pp
            join plan_targets pt on pt.production_plan_id = pp.production_plan_id
            join execution_log el on el.target_id = pt.plan_target_id
            join final_stage fs on fs.product_id = pp.product_id
                and el.stage_id = fs.stage_id and el.process_id = fs.config_id
            where pp.production_plan_id = :production_plan_id
            and pp.deleted is not true and pt.deleted is not true and el.deleted is not true
            group by pp.production_plan_id, pp.product_id, el.stage_id
        )
        select coalesce(sum(sq.outward_qty * coalesce(ec.rate, 0)), 0) as estimated_cost
        from stage_qty sq
        left join estimated_cost ec on ec.product_id = sq.product_id and ec.stage_id = sq.stage_id
    """)
    result = s.execute(query, {"production_plan_id": production_plan_id, "compcode": compcode}).fetchone()
    return float(result[0]) if result and result[0] else 0.0

def get_estimated_material_cost(s, production_plan_id, compcode):
    query = text(f"""
        with plan_base as (
            select pp.production_plan_id, 
                   COALESCE(ppp.product_id, pp.product_id) as primary_product_id,
                   COALESCE(ppp.planned_quantity, pp.planed_quantity) as planned_quantity
            from production_plan pp
            left join production_plan_products ppp on ppp.production_plan_id = pp.production_plan_id and ppp.deleted is not true
            where pp.production_plan_id = :production_plan_id and pp.deleted is not true
        ),
        plan_units as (
            select pb.production_plan_id,
                   pb.primary_product_id,
                   coalesce(pi.product_id, pb.primary_product_id) as bom_product_id,
                   (coalesce(pb.planned_quantity, 0) * coalesce(pi.needded_count, 1)::numeric) as effective_quantity
            from plan_base pb
            left join package_items pi on pi.pakage_id = pb.primary_product_id and pi.deleted is not true and pi.is_package_material is not true
        )
        select coalesce(sum(
            (pu.effective_quantity / nullif(coalesce(pb.planned_quantity, 1), 0))
            * coalesce(bc.quantity::numeric, 0) 
            * coalesce(mc.cost, 0)
        ), 0) as estimated_cost
        from plan_units pu
        join plan_base pb on pb.production_plan_id = pu.production_plan_id and pb.primary_product_id = pu.primary_product_id
        left join bom b on b.product_id = pu.bom_product_id and b.compcode = :compcode and b.deleted is not true
        left join bom_component bc on bc.bom_id = b.bom_id and bc.deleted is not true
            and bc.product_id not in (select product_id from bom where deleted is not true and product_id is not null)
        left join material_cost mc on mc.product_id = bc.product_id
    """)
    result = s.execute(query, {"production_plan_id": production_plan_id, "compcode": compcode}).fetchone()
    return float(result[0]) if result and result[0] else 0.0

def get_material_cost_bulk(production_plan_ids, start_date=None, end_date=None):
    if not production_plan_ids:
        return {}
    
    date_con = ""
    params = {"production_plan_ids": list(set(production_plan_ids))}
    if start_date and end_date:
        date_con = " AND execution_date >= cast(:start_date as date) AND execution_date <= cast(:end_date as date) "
        params["start_date"] = start_date
        params["end_date"] = end_date

    query = text(f"""
        SELECT production_plan_id, sum(actual_material_cost) as total_cost 
        FROM mv_daily_manufacturing_fact
        WHERE production_plan_id IN :production_plan_ids {date_con}
        GROUP BY production_plan_id
    """).bindparams(bindparam('production_plan_ids', expanding=True))
    
    from .. import db_client
    from ipss_utils.ipss_db import query_to_dict
    result = query_to_dict(db_client.engine.execute(query, **params))
    return {row['production_plan_id']: float(row['total_cost'] or 0) for row in result}

def get_estimated_labour_cost_bulk(s, production_plan_ids, compcode=None, start_date=None, end_date=None):
    if not production_plan_ids:
        return {}
    date_con = ""
    params = {"production_plan_ids": list(set(production_plan_ids))}
    if start_date and end_date:
        date_con = " AND execution_date >= cast(:start_date as date) AND execution_date <= cast(:end_date as date) "
        params["start_date"] = start_date
        params["end_date"] = end_date

    query = text(f"""
        SELECT production_plan_id, product_id, coalesce(sum(estimated_labour_cost), 0) as estimated_cost
        FROM mv_daily_manufacturing_fact
        WHERE production_plan_id IN :production_plan_ids {date_con}
        GROUP BY production_plan_id, product_id
    """).bindparams(bindparam('production_plan_ids', expanding=True))
    result = s.execute(query, params).fetchall()
    return {(row[0], row[1]): float(row[2]) for row in result}

def get_estimated_material_cost_bulk(s, production_plan_ids, compcode=None, start_date=None, end_date=None):
    if not production_plan_ids:
        return {}
    
    unique_plan_ids = list(set(production_plan_ids))
    params = {"production_plan_ids": unique_plan_ids}
    compcode_clause = ""
    if compcode:
        compcode_clause = " AND (b.compcode = :compcode OR b.compcode IS NULL) "
        params["compcode"] = compcode

    query = text(f"""
        WITH plan_base AS (
            SELECT 
                pp.production_plan_id,
                COALESCE(ppp.product_id, pp.product_id) AS product_id,
                COALESCE(ppp.planned_quantity, pd.plan_quantity, pp.planed_quantity, 0)::numeric AS planned_quantity
            FROM production_plan pp
            LEFT JOIN production_plan_products ppp ON ppp.production_plan_id = pp.production_plan_id AND ppp.deleted IS NOT TRUE
            LEFT JOIN plan_details pd ON pd.production_plan_id = pp.production_plan_id AND pd.deleted IS NOT TRUE
            WHERE pp.production_plan_id IN :production_plan_ids AND pp.deleted IS NOT TRUE
        ),
        plan_base_distinct AS (
            SELECT DISTINCT ON (production_plan_id, product_id)
                production_plan_id,
                product_id,
                planned_quantity
            FROM plan_base
            ORDER BY production_plan_id, product_id, planned_quantity DESC
        ),
        plan_exploded AS (
            SELECT 
                pbd.production_plan_id,
                pbd.product_id,
                pbd.planned_quantity,
                COALESCE(pi.product_id, pbd.product_id) AS bom_target_product_id,
                COALESCE(pi.needded_count, 1)::numeric AS pack_multiplier
            FROM plan_base_distinct pbd
            LEFT JOIN package_items pi ON pi.pakage_id = pbd.product_id 
                AND pi.deleted IS NOT TRUE 
                AND pi.is_package_material IS NOT TRUE
        ),
        bom_costs AS (
            SELECT 
                pe.production_plan_id,
                pe.product_id,
                COALESCE(SUM(
                    pe.planned_quantity 
                    * pe.pack_multiplier 
                    * CAST(NULLIF(bc.quantity, '')::numeric AS numeric) 
                    * COALESCE(mc.cost, 0)
                ), 0) AS estimated_cost
            FROM plan_exploded pe
            JOIN bom b ON b.product_id = pe.bom_target_product_id 
                AND b.deleted IS NOT TRUE 
                {compcode_clause}
            JOIN bom_component bc ON bc.bom_id = b.bom_id 
                AND bc.deleted IS NOT TRUE
                -- Prevent double-counting manufactured sub-assemblies (e.g. cutting parts) that have their own plans
                AND bc.product_id NOT IN (
                    SELECT product_id FROM bom WHERE deleted IS NOT TRUE AND product_id IS NOT NULL
                )
            LEFT JOIN material_cost mc ON mc.product_id = bc.product_id
            GROUP BY pe.production_plan_id, pe.product_id
        )
        SELECT production_plan_id, product_id, estimated_cost
        FROM bom_costs
    """).bindparams(bindparam('production_plan_ids', expanding=True))

    result = s.execute(query, params).fetchall()
    return {(row[0], row[1]): float(row[2]) for row in result}


def get_labour_cost_bulk(s, production_plan_ids, start_date=None, end_date=None):
    if not production_plan_ids:
        return {}
        
    date_con = ""
    params = {"production_plan_ids": list(set(production_plan_ids))}
    if start_date and end_date:
        date_con = " AND execution_date >= cast(:start_date as date) AND execution_date <= cast(:end_date as date) "
        params["start_date"] = start_date
        params["end_date"] = end_date

    query = text(f"""
    WITH labour_sum AS (
        SELECT
            production_plan_id,
            product_id,
            COALESCE(SUM(actual_labour_cost), 0) AS total_labour_cost
        FROM mv_daily_manufacturing_fact
        WHERE production_plan_id IN :production_plan_ids {date_con}
        GROUP BY production_plan_id, product_id
    )
    SELECT 
        ls.production_plan_id,
        ls.product_id,
        ls.total_labour_cost,
        COALESCE(
            ls.total_labour_cost / NULLIF(
                COALESCE(
                    NULLIF(COALESCE(ppp.moved_quantity, pp.moved_quantity), 0),
                    (SELECT SUM(el2.outward_qty) 
                     FROM execution_log el2 
                     JOIN plan_targets pt2 ON pt2.plan_target_id = el2.target_id 
                     WHERE pt2.production_plan_id = ls.production_plan_id 
                       AND el2.deleted IS NOT TRUE)
                ), 
                0
            ), 
            0
        ) AS labour_cost_per_product
    FROM labour_sum ls
    JOIN production_plan pp ON pp.production_plan_id = ls.production_plan_id
    LEFT JOIN production_plan_products ppp ON ppp.production_plan_id = ls.production_plan_id 
        AND ppp.product_id = ls.product_id AND ppp.deleted IS NOT TRUE
    """).bindparams(bindparam('production_plan_ids', expanding=True))
    result = s.execute(query, params).fetchall()
    return {(row[0], row[1]): {"total_labour_cost": float(row[2]), "labour_cost_per_product": float(row[3])} for row in result}
