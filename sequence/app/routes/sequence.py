from flask_restx import Namespace, Resource, fields
from ..api_doc import product_group, attribute_ids, product_group_name, attribute_ids_name
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes

productGroupApiRoutes = Namespace('productGroupSequence', path='/am-product_group_seq')

attribute_ids_model = productGroupApiRoutes.model('attribute_ids_model',attribute_ids)


attribute_ids_name_model = productGroupApiRoutes.model('attribute_ids_model',attribute_ids_name)

postModel = productGroupApiRoutes.model('postModel',
            {**product_group,
                    "attributes": fields.List(fields.Nested(attribute_ids_model))})

getModel = productGroupApiRoutes.model('getModel',{
    **product_group_name,
    'attributes': fields.List(fields.Nested(attribute_ids_name_model))
})


listResponse=productGroupApiRoutes.model('listResponse',{
    **list_response_model,
    **{"data":fields.List(fields.Nested(getModel))}
})

update_record_response_model = productGroupApiRoutes.model('response', update_record_response)
