import pandas as pd
import json

def dataFormating(df=[]):
    df = pd.DataFrame(df)
    grouped_data = []

    for plan_unique, plan_group in df.groupby('plan_unique'):
        plan_row = plan_group.iloc[0]

        request_list = []
        for request_id, req_group in plan_group.groupby('request_id'):
            # Filter only rows with a valid dispatch_date
            dispatched_rows = req_group[req_group['dispatch_date'].notna()]

            order_date_list = []
            for dispatch_date, date_group in dispatched_rows.groupby('dispatch_date'):
                distpatch_data_list = []
                # Drop duplicates caused by multiple planned products (fn.sku_id etc) in SQL join
                unique_date_group = date_group.drop_duplicates(subset=['sku_id', 'action', 'product_code'])
                for _, row in unique_date_group.iterrows():
                    distpatch_data_list.append({
                        "dispatch_amount": row["dispatch_amount"],
                        "action": row["action"],
                        "product_name": row["product_name"],
                        "sku_id": row["sku_id"],
                        "approved_amount": row["approved_amount"],
                        "requested_amount": row["requested_amount"],
                        "request_status": row["request_status"],
                        "approval_date": row["approval_date"],
                        "product_code": row["product_code"]
                    })

                order_date_list.append({
                    "dispatch_date": str(dispatch_date),
                    "distpatch_data": distpatch_data_list
                })

            # Always include the request_id (even if no dispatch), set product_count accordingly
            request_list.append({
                "request_id": request_id,
                "product_count": dispatched_rows['sku_id'].nunique() if not dispatched_rows.empty else 0,
                "order_date": order_date_list
            })

        grouped_data.append({
            "plan_unique": plan_row["plan_unique"],
            "order_unique": plan_row["order_unique"] if "order_unique" in plan_row and pd.notnull(plan_row["order_unique"]) else "-",
            "total_value": int(plan_row["total_value"]),
            "planned_wastage": plan_row["planned_wastage"],
            "planned_wastage_per": plan_row["planned_wastage_per"],
            "status": plan_row["status"],
            "plan_date": str(plan_row["plan_date"]),
            "planed_quantity": plan_row["planed_quantity"],
            "planned_product": plan_row["planned_product"],
            "planned_product_code": plan_row["planned_product_code"],
            "planned_product_sku": plan_row["planned_product_sku"],
            "request_data": request_list
        })

    return grouped_data

# import pandas as pd
# import json
#
# # Assuming `df` is your DataFrame from the SQL query
# # Example: df = p+
# def dataFormating(df=[]):
#     df = pd.DataFrame(df)
#     grouped_data = []
#
#     for (plan_unique), plan_group in df.groupby('plan_unique'):
#         plan_row = plan_group.iloc[0]
#
#         # Group by request_id
#         request_list = []
#         for request_id, req_group in plan_group.groupby('request_id'):
#             # Group by dispatch_date
#             order_date_list = []
#             for dispatch_date, date_group in req_group.groupby('dispatch_date'):
#                 distpatch_data_list = []
#                 for _, row in date_group.iterrows():
#                     distpatch_data_list.append({
#                         "dispatch_amount": row["dispatch_amount"],
#                         "action": row["action"],
#                         "product_name": row["product_name"],
#                         "sku_id": row["sku_id"],
#
#                         "approved_amount": row["approved_amount"],
#                         "requested_amount": row["requested_amount"],
#                         "request_status": row["request_status"],
#                         "approval_date": row["approval_date"],
#                         "product_code":row['product_code']
#                     })
#
#                 order_date_list.append({
#                     "dispatch_date": str(dispatch_date),
#                     "distpatch_data": distpatch_data_list
#                 })
#
#             request_list.append({
#                 "request_id": request_id,
#                 "product_count": sum(len(date_group) for _, date_group in req_group.groupby('dispatch_date')),
#                 # "product_count": int(req_group["product_count"].iloc[0]) if pd.notnull(req_group["product_count"].iloc[0]) else 0,
#                 "order_date": order_date_list
#             })
#
#         grouped_data.append({
#             "plan_unique": plan_row["plan_unique"],
#             "total_value": int(plan_row["total_value"]),
#             "planned_wastage": plan_row["planned_wastage"],
#             "planned_wastage_per": plan_row["planned_wastage_per"],
#             "status": plan_row["status"],
#             "plan_date": str(plan_row["plan_date"]),
#             "planed_quantity": plan_row["planed_quantity"],
#             "planned_product": plan_row["planned_product"],
#             "planned_product_code":plan_row['planned_product_code'],
#             "planned_product_sku": plan_row["planned_product_sku"],
#             "request_data": request_list
#         })
#
#     # Convert to JSON
#     # json_output = json.dumps(grouped_data, indent=2, default=str)
#     # print(grouped_data)
#     return grouped_data
