from sqlalchemy import text
from flask import Flask
from sqlalchemy import create_engine
import json

engine = create_engine('postgresql://postgres:postgres@localhost:5432/ipss')

sql_query=text(f'''
        SELECT pp.plan_unique,
       COALESCE(ppp.product_id, pp.product_id) as product_id,
       pp.wastage AS allowed_wastage,
       p.product_code,
       p.product_name,
       oie.quantity_ordered,
       pp.planed_quantity,
       pp.production_plan_id, 
       u.id as uom_id,
	   u.uom,
       round(sum(case when asm.is_final_process is true or asm.activity_stage_map_id is null then el.outward_qty 
       else 0 end),2) as outward_qty,
       round(avg(el.wastage),2) as actual_wastage,
       s.stage_name,
       cp.order_unique,
       p.sku_id
FROM production_plan pp
LEFT JOIN production_plan_products ppp ON ppp.production_plan_id = pp.production_plan_id
JOIN products p ON p.product_id = COALESCE(ppp.product_id, pp.product_id)
left join uom as u on p.uom_id = u.id
join plan_details as pd on pp.production_plan_id = pd.production_plan_id
left join order_items_extract as oie on oie.extract_id = pd.order_extract_id
left join customer_purchase_items as cpi on cpi.items_id = oie.order_items_id
left join customer_purchase as cp on cpi.customer_purchase_id =cp.customer_purchase_id
JOIN (
    SELECT product_id, MAX(rank_id) AS max_rank_id
    FROM production_stages
    where deleted is not true
    GROUP BY product_id
) ps_max ON ps_max.product_id = COALESCE(ppp.product_id, pp.product_id)
LEFT JOIN production_stages ps ON ps.product_id = COALESCE(ppp.product_id, pp.product_id) AND ps.rank_id = ps_max.max_rank_id and ps.deleted is not true
left join stage s on s.stage_id =ps.stage_id 
LEFT JOIN plan_targets pt ON pt.production_plan_id = pp.production_plan_id AND pt.product_id = COALESCE(ppp.product_id, pp.product_id)
LEFT JOIN execution_log el ON el.target_id = pt.plan_target_id and el.stage_id=s.stage_id
left join activity_stage_map asm on asm.production_stage_id =ps.id and asm.config_id=el.process_id
where pp.deleted is not true
group by pp.plan_unique,COALESCE(ppp.product_id, pp.product_id),pp.wastage,p.product_code,p.product_name,oie.quantity_ordered,s.stage_name,p.sku_id,pp.planed_quantity,pp.production_plan_id,
u.id,
u.uom,
cp.order_unique
        limit 10 offset 0
        ''')

result = engine.execute(sql_query).fetchall()
print("Result:")
for r in result:
    print(dict(r))

sql_count=text(f'''
        select count(distinct pp.production_plan_id )
        FROM production_plan pp
        LEFT JOIN production_plan_products ppp ON ppp.production_plan_id = pp.production_plan_id
        join production_stages ps on ps.product_id = COALESCE(ppp.product_id, pp.product_id)
        where pp.deleted is not true 
        ''')
count = engine.execute(sql_count).scalar()
print("Count:", count)
