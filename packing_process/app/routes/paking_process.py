from flask_restx import Namespace, Resource, fields


from ..api_doc import paking_process_fields, packing_materials_fields
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes

paking_process_api_route = Namespace('paking_process', path='/paking_process')

# List paking_processs API docs
packing_materials_model=paking_process_api_route.model('packing_materials_model',packing_materials_fields)
paking_process_model = paking_process_api_route.model('paking_processs_model', {
            **paking_process_fields,
    "items":fields.List(fields.Nested(packing_materials_model))
        })
create_response_model=paking_process_api_route.model('create_response_model',create_record_response)

#getservice

packing_materials_get_model=paking_process_api_route.model('packing_materials_get_model', {**packing_materials_fields,
                                        "product_code":fields.String,
                                        "product_name":fields.String,
                                        "sku_id":fields.String})
paking_process_get_model = paking_process_api_route.model('paking_process_get_model', {
            **paking_process_fields,
"product_code":fields.String,
    "order_unique":fields.String,
                                        "product_name":fields.String,
                                        "sku_id":fields.String,
    "items":fields.List(fields.Nested(packing_materials_get_model))
        })
packing_list_response=paking_process_api_route.model('packing_list_response',{
    **list_response_model,
    "results":fields.List(fields.Nested(paking_process_get_model))
})



#########################
alter_respnse_model=paking_process_api_route.model('alter_respnse_model', {**paking_process_fields,
                                                                           "quantity_ordered":fields.String,
                                                                           "planned_quantity":fields.String,
                                                                           "product_count":fields.String,
                                                                           "product_id":fields.Integer,
                                                                           "product_code": fields.String,
                                                                           "product_name": fields.String,
                                                                           "sku_id": fields.String,
                                                                           "order_unique":fields.String
                                                                           })
final_response_model=paking_process_api_route.model('final_response_model',{
    **list_response_model,
    "results":fields.List(fields.Nested(alter_respnse_model))
})


bulk_post_model=paking_process_api_route.model('bulk_post_model',{
    "data":fields.List(fields.Nested(alter_respnse_model))
})