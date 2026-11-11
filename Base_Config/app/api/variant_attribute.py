import datetime

from flask import request
from flask_restx import Resource, abort
# from .. import ipss_db
from ipss_utils.ipss_api_doc import list_api_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
# from ..api_doc import variant_attributes_roles_fields
from ..models.variant_attribute import VariantAttribute
from ipss_utils.decorators import login_required

from ..routes.variant_attribute import variant_attribute_api_route, variant_attribute_list_response, \
    create_variant_attribute_response, update_variant_attribute_model, update_variant_attribute_response, \
    bulk_post_model
# from sqlalchemy import and_, text
from ..routes.variant_attribute import get_variant_attribute_response
from .. import ipss_db, db_client
from .errorhandling import map_sqlalchemy_error_to_http_status,update_local

# Primary p_key name

primary_key = 'variant_attribute_id'

@variant_attribute_api_route.route('/')
class VariantAttributeApi(Resource):
    per_page = 20
    @variant_attribute_api_route.marshal_with(variant_attribute_list_response)
    @variant_attribute_api_route.doc(params=list_api_params)
    @login_required(permissions='variant-attribute.list||variant-value.add||variant-value.edit')
    def get(self):
        """
        List of variant_attribute with pagination
        TODO: Search
        :return:
        """

        curr = request.args.get('current_user', {})
        compcode = curr.get('company_id', None)
        result_per_page = request.args.get('results_per_page', 20)
        page = request.args.get("page", 1)
        offset = (page - 1) * result_per_page if (page - 1) * result_per_page else 0
        # Filtering by parent id (Primary Table ID)
        sql_con = ''
        variant_attribute_id = request.args.get('variant_attribute_id', None)

        if variant_attribute_id:
            sql_con += ' and variant_attribute.variant_attribute_id=:variant_attribute_id'

        query  = text(f'''
        select * from variant_attribute where compcode=:compcode and deleted is not true {sql_con} and 1=1
        order by created_on desc
        limit :limit offset :offset
        ''')
        query_count = text(f'''
        select count(*) from variant_attribute where compcode=:compcode and deleted is not true {sql_con} and 1=1
        limit :limit offset :offset
        ''')

        result = query_to_dict(db_client.engine.execute(query,compcode=compcode, variant_attribute_id=variant_attribute_id, limit=result_per_page,offset=offset))
        count = query_to_dict(db_client.engine.execute(query_count, compcode=compcode, variant_attribute_id=variant_attribute_id, limit=result_per_page,offset=offset))

        return {
            'total_results': count[0].get('count', None) if count else 0,
            'page': page,
            'results_per_page': result_per_page,
            "results": result
        }

    @login_required(permissions='variant-attribute.add')
    @variant_attribute_api_route.expect(bulk_post_model)
    @variant_attribute_api_route.marshal_with(create_variant_attribute_response)
    def post(self):
        """
        Create variant_attribute record and return inserted id
        :return:
        """
        data = request.json
        data = data.get('data', None)
        compcode = request.args.get('current_user', {})
        cc = {"compcode": compcode.get('company_id'),
              "created_on": str(datetime.datetime.now()),
              "created_by": compcode.get('username')
              # "product_id": pkey if pkey else result.get('primary_key_id')[0]
              }
        updateData = [{**data.pop(i), **cc} for i in range(len(data) - 1, -1, -1) if
                      data[i].get('variant_attribute_id')]
        data = [{**i, **cc} for i in data]
        error = ''
        message = None
        try:
            with db_client.session.begin():

                if updateData:
                    db_client.session.bulk_update_mappings(mapper=VariantAttribute, mappings=updateData)
                if data:
                    db_client.session.bulk_insert_mappings(mapper=VariantAttribute, mappings=data)
        except SQLAlchemyError as e:
            # error = str(e)
            db_client.session.rollback()
            db_client.session.flush()
            res = map_sqlalchemy_error_to_http_status(e)
            print("FGH", res)
            return res
        success = False if error else True
        if success:
            message = "Records created Successfully"
        return {
            'success': success,
            'message': message,
            'error': error,
        }
@variant_attribute_api_route.route('/<variant_attribute_id>/')
class EmployeeUpdateApi(Resource):
    @staticmethod
    def update_record(data, variant_attribute_id):
        data.pop('variant_attribute_id', None)

        result = update_local(
            model=VariantAttribute,
            condition=VariantAttribute.variant_attribute_id == variant_attribute_id,
            values=data
        )
        return result

    @variant_attribute_api_route.marshal_with(get_variant_attribute_response)
    @login_required(permissions='variant-attribute.view')
    def get(self, variant_attribute_id):
        """
        Read user record / single record
        :param id:
        :return:
        """

        user = VariantAttribute.query.filter_by(variant_attribute_id=int(variant_attribute_id)).first()
        return user

    @variant_attribute_api_route.expect(update_variant_attribute_model)
    @variant_attribute_api_route.marshal_with(update_variant_attribute_response)
    @login_required(permissions='variant-attribute.edit')
    def put(self, variant_attribute_id):
        """
        Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, variant_attribute_id)
        return response

    @variant_attribute_api_route.expect(update_variant_attribute_model)
    @variant_attribute_api_route.marshal_with(update_variant_attribute_response)
    @login_required(permissions='variant-attribute.edit')
    def patch(self, variant_attribute_id):
        """
        Partial Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, variant_attribute_id)
        return response

    @variant_attribute_api_route.marshal_with(update_variant_attribute_response)
    @login_required(permissions='variant-attribute.delete')
    def delete(self, variant_attribute_id):
        """
        Soft delete VariantAttribute record
        TODO: Make soft delete
        :return:
        """

        result = ipss_db.update_record(
            model=VariantAttribute,
            condition=VariantAttribute.variant_attribute_id == variant_attribute_id,

            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result

######################################################################

    
    
