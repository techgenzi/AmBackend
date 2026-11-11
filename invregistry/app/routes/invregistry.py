from flask_restx import Namespace, Resource, fields
from ..api_doc import invRegistryFields, stock_list, store_product, transfer_log, transfer_get_log, inventory_action, stock_movement_report, report_date_params
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes

invRegistry_api_route = Namespace('InventoryRgistry', path='/am-invregistry/InventoryRgistry')

stockList_api_route = Namespace('StockList', path='/am-invregistry/stocklist')

stock_list_model = stockList_api_route.model('stock_list_model', stock_list)

stock_list_response = stockList_api_route.model('stock list  model', {
    **list_response_model,
    'results': fields.List(fields.Nested(stock_list_model))
})

stock_movement_report_model = stockList_api_route.model('stock_movement_report_model', stock_movement_report)
stock_movement_response = stockList_api_route.model('stock_movement_response', {
    **list_response_model,
    'results': fields.List(fields.Nested(stock_movement_report_model))
})
# List inventoryRegistry API docs
inventoryRegistry_model = invRegistry_api_route.model('inventoryRegistry_model', {
            **invRegistryFields ,**{"sku_id":fields.String,
                                    "uom":fields.String,
                                    "product_count":fields.String,
                                    "product_code":fields.String,
                                    "product_name":fields.String,
                                    'allocated_quantity': fields.String,
                                    'store_id': fields.Integer,
                                    'store_name': fields.String,
                                    "rawmaterialsid":fields.String,
                                    "asset_attributes":fields.Raw,
                                    "unit_cost":fields.Float,
                                    "weighted_avg_rate":fields.Float,
                                    "last_grn_rate":fields.Float}
        })
inventoryBulk_model=invRegistry_api_route.model('inventoryBulk_model',{
    'data':fields.List(fields.Nested(inventoryRegistry_model))
})

inven_res = invRegistry_api_route.model('model',{
    'prod_plan_id':fields.Integer,
    'packing_process_id': fields.Integer,
    'plan_unique': fields.String,
    'package_unique': fields.String,
    'type': fields.String,
    'ref_id': fields.String,
    'requested_by': fields.String,
    'requested_on': fields.String,
    'status': fields.String,
    'order_unique': fields.String,
    'lot_no': fields.String,
    'data': fields.List(fields.Nested(inventoryRegistry_model))
})


inventoryRegistry_list_response = invRegistry_api_route.model('inventoryRegistry_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(inven_res))
    }
})

create_inventoryRegistry_model = invRegistry_api_route.model('create_inventoryRegistry_model', inventoryRegistry_model)
create_inventoryRegistry_response = invRegistry_api_route.model('create_inventoryRegistry_response', create_record_response)

# Get inventoryRegistry records model
get_inventoryRegistry_response = invRegistry_api_route.model('get_inventoryRegistry_response', invRegistryFields)

# Update user record
update_inventoryRegistry_fields = invRegistryFields
update_inventoryRegistry_model = invRegistry_api_route.model('update_inventoryRegistry_model', invRegistryFields)
update_inventoryRegistry_response = invRegistry_api_route.model('update_inventoryRegistry_response', update_record_response)

manual_addition_model = invRegistry_api_route.model('manula_addition_model', {
                                                                            'product_code': fields.String, **invRegistryFields,
                                                                            "uom": fields.String,
                                                                            'uom_id': fields.Integer,
                                                                            'sku_id': fields.String,
                                                                            'store_name': fields.String})

manual_list_response_model = invRegistry_api_route.model('manual_list_response_model', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(manual_addition_model))
    }
})

manual_post_model = invRegistry_api_route.model('manual+_post',{
    'data': fields.List(fields.Nested(manual_addition_model))
})

store_product_model = stockList_api_route.model('store_product_model', store_product)

store_product_list_model = stockList_api_route.model('store_product_list_model', {
    **list_response_model,
    'results': fields.List(fields.Nested(store_product_model))
})

transfer_log_model = invRegistry_api_route.model('transfer_log_model', transfer_log)

transfer_post_model = invRegistry_api_route.model('transfer_post_model', {
    'data': fields.List(fields.Nested(transfer_log_model))
})

transfer_get_model = invRegistry_api_route.model('transfer_get_model', transfer_get_log)


transfer_get_list_response = invRegistry_api_route.model('transfer_get_list_resposne', {
    **list_response_model,
    'results': fields.List(fields.Nested(transfer_get_model))
})

inventory_action_model = invRegistry_api_route.model('inventory_action_model', inventory_action)

inventory_report_response = invRegistry_api_route.model('inventory_report_response', {
    **list_response_model,
    'results': fields.List(fields.Nested(inventory_action_model))
})


# Models for Reconciliation
leak_stat_model = invRegistry_api_route.model('leak_stat_model', {
    'count': fields.Integer,
    'total_amount': fields.Float
})

unissued_request_model = invRegistry_api_route.model('unissued_request_model', {
    'material_request_id': fields.String,
    'requested_by': fields.String,
    'requested_on': fields.String,
    'prod_plan_id': fields.Integer
})

reconciliation_alerts_response = invRegistry_api_route.model('reconciliation_alerts_response', {
    'orphaned_allocations': fields.Nested(leak_stat_model),
    'dispatched_leaks': fields.Nested(leak_stat_model),
    'rejected_leaks': fields.Nested(leak_stat_model),
    'approved_unissued_requests': fields.List(fields.Nested(unissued_request_model))
})

reconcile_post_model = invRegistry_api_route.model('reconcile_post_model', {
    'action': fields.String(required=True, description="Action to perform: clear_orphaned, clear_dispatched, clear_rejected, reverse_request"),
    'ref_id': fields.String(description="Reference ID for reverse_request action")
})

reconcile_response = invRegistry_api_route.model('reconcile_response', {
    'success': fields.Boolean,
    'action': fields.String,
    'updated_rows': fields.Integer
})
##############################################



# Stock Audit & Discrepancies Models
stock_audit_item_model = invRegistry_api_route.model('stock_audit_item_model', {
    'product_id': fields.Integer,
    'product_code': fields.String,
    'product_name': fields.String,
    'sku_id': fields.String,
    'uom': fields.String,
    'store_id': fields.Integer,
    'store_name': fields.String,
    'physical_stock': fields.Float,
    'ledger_stock': fields.Float,
    'variance': fields.Float,
    'allocated_quantity': fields.Float,
    'diagnosed_reason': fields.String,
    'suggested_action': fields.String,
    'suggested_qty': fields.Float
})

stock_audit_summary_model = invRegistry_api_route.model('stock_audit_summary_model', {
    'total_products': fields.Integer,
    'healthy_count': fields.Integer,
    'discrepant_count': fields.Integer,
    'net_variance': fields.Float,
    'unrecorded_opening_count': fields.Integer,
    'over_dispatched_count': fields.Integer,
    'other_discrepancy_count': fields.Integer
})

stock_audit_response = invRegistry_api_route.model('stock_audit_response', {
    'summary': fields.Nested(stock_audit_summary_model),
    'items': fields.List(fields.Nested(stock_audit_item_model)),
    'total_results': fields.Integer,
    'page': fields.Integer,
    'results_per_page': fields.Integer
})

stock_audit_drilldown_response = invRegistry_api_route.model('stock_audit_drilldown_response', {
    'product_id': fields.Integer,
    'product_name': fields.String,
    'product_code': fields.String,
    'physical_stock': fields.Float,
    'ledger_stock': fields.Float,
    'variance': fields.Float,
    'total_inward': fields.Float,
    'total_outward': fields.Float,
    'total_manual_addition': fields.Float,
    'total_manual_deduction': fields.Float,
    'recent_transactions': fields.List(fields.Raw)
})

stock_reconcile_item_model = invRegistry_api_route.model('stock_reconcile_item_model', {
    'product_id': fields.Integer(required=True),
    'store_id': fields.Integer(required=False),
    'sub_location': fields.String(required=False),
    'adjustment_qty': fields.Float(required=True),
    'action': fields.String(required=True, description='manual_addition or manual_deduction'),
    'reason': fields.String(required=False),
    'update_physical_stock': fields.Boolean(default=False)
})

stock_audit_reconcile_post_model = invRegistry_api_route.model('stock_audit_reconcile_post_model', {
    'adjustments': fields.List(fields.Nested(stock_reconcile_item_model), required=True)
})
