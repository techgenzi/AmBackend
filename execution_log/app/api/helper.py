from pprint import pprint
from sqlalchemy import text
from .. import db_client
def calculate_avg_efficiency(data,employee_map):
    result = []
    # pprint(data[0])
    for employee in data:
        efficiency_sums = {}
        efficiency_counts = {}
        emp_id = employee.get('emp_id')
        employee_data = employee_map.get(emp_id, {})
        idcardno = employee_data.get('idcardno', 'Unknown')
        employee_name = employee_data.get('employee_name')
        start_date = employee["opertaion_start_date"]

        # Aggregate efficiency values from all products
        for product in employee["products"]:
            for hour, value in product["efficiency"].items():
                if hour not in efficiency_sums:
                    efficiency_sums[hour] = 0
                    efficiency_counts[hour] = 0
                efficiency_sums[hour] += value if value else 0
                efficiency_counts[hour] += 1

        # Compute average efficiency for each hour
        avg_efficiency = {
            hour: round(efficiency_sums[hour], 2)
            for hour in efficiency_sums
        }

        result.append({
            "idcardno": idcardno,
            'opertaion_start_date': start_date,
            "employee_name": employee_name,
            "average_efficiency": avg_efficiency,
            "total_count":employee["total_count"],
            "overall_efficiency":sum(avg_efficiency.values()),
            "products": employee["products"]
        })

    return result


def get_labour_cost(emp_id, plan_target_id, outward_qty, s=db_client.session,):

    query = text(f'''
    with cte as(
        select pt.target_quantity from plan_targets pt
        where pt.plan_target_id =:plan_target_id
	)
	SELECT
        round(CASE
            WHEN hr.daily_wages = TRUE THEN
                (NULLIF(hr.ctc_amount, '')::numeric / 8) *
                (:outward_qty / NULLIF(cte.target_quantity, 0))
            ELSE
                (NULLIF(hr.ctc_amount, '')::numeric / (30 * 8)) *
                (:outward_qty / NULLIF(cte.target_quantity, 0))
        END ,2)
        AS working_wage
    FROM 
    hremploymast hr
    cross join cte 
    where hr.hremploymastid =:emp_id
''')

    res = s.execute(query, {'emp_id': emp_id, 'outward_qty': outward_qty, 'plan_target_id': plan_target_id})
    row = res.fetchone()
    total_cost = row["working_wage"] if row and row["working_wage"] is not None else 0
    return total_cost
