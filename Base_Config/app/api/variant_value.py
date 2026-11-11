import datetime
from flask import request, session
from flask_restx import Resource, abort
from ..redis_client.redis_client import redis_client
from ipss_utils.ipss_api_doc import list_api_params, search_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, func, distinct, BigInteger
from sqlalchemy.exc import SQLAlchemyError

from .helper import check_all_hash, check_product_code_associated_to_variant_value
# from ..api_doc import variant_values_roles_fields
from ..models.variant_value import VariantValue
from ipss_utils.decorators import login_required
from .errorhandling import map_sqlalchemy_error_to_http_status
from ..routes.variant_value import variant_value_api_route, variant_value_list_response, create_variant_value_response,     update_variant_value_model, update_variant_value_response
# from sqlalchemy import and_, text
from ..routes.variant_value import create_variant_value_model, get_variant_value_response,bulk_post_model
from .. import ipss_db, db_client
from ..api_doc.varient_value_api_doc import search_filters
from .errorhandling import map_sqlalchemy_error_to_http_status,update_local
# Primary p_key name
primary_key = 'variant_value_id'


@variant_value_api_route.route('/')
class VariantValueApi(Resource):
    per_page = 20
    @variant_value_api_route.marshal_with(variant_value_list_response)
    @variant_value_api_route.doc(params={**list_api_params,**search_filters})
    @login_required(permissions='variant-value.list||product-group.add||product-group.edit')
    def get(self):
        """
        List of variant_value with pagination
        TODO: Search
        :return:
        """

        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page if (paged - 1) * results_per_page else 0
        sql_con = ''
        variant_attribute_id = request.args.get('variant_attribute_id', None)
        if variant_attribute_id:
            sql_con += " and variant_value.variant_attribute_id=:variant_attribute_id "

        query = text(f'''
        select variant_value.*,variant_attribute.variant_attribute_name from variant_value left join
        variant_attribute
         on variant_value.variant_attribute_id = variant_attribute.variant_attribute_id
         where variant_value.deleted is not true and variant_value.compcode =:compcode {sql_con} and 1=1
        order by created_on desc
        limit :limit offset :offset
        ''')
        query_count = text(f'''
        select count(*) from variant_value where variant_value.deleted is not true and variant_value.compcode =:compcode {sql_con} and 1=1
        limit :limit offset :offset
        ''')
        result = query_to_dict(db_client.engine.execute(query,
                                                           limit=results_per_page,
                                                           offset=offset,
                                                           compcode=compcode,
                                                           variant_attribute_id=variant_attribute_id
                                                    ))
        count = query_to_dict(db_client.engine.execute(query_count,
                                                       limit=results_per_page,
                                                       offset=offset,
                                                       compcode=compcode,
                                                       variant_attribute_id=variant_attribute_id
                                                    ))
        return {
            "total_results": count[0].get('count', 0) if count else 0,
            "page": paged,
            "results_per_page": results_per_page,
            "results": result
        }

    @login_required(permissions='variant-value.add')
    @variant_value_api_route.expect(bulk_post_model)
    @variant_value_api_route.marshal_with(create_variant_value_response)
    def post(self):
        """
        Create variant_value record and return inserted id
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
        # updateData = [{**data.pop(i), **cc} for i in range(len(data) - 1, -1, -1) if
        #               data[i].get('variant_attribute_id')]
        data = [{**i, **cc, "variant_value_temp": i.get("variant_value", "").replace(" ", "").lower()} for i in data]
        error = ''
        try:
            with db_client.session.begin():
                # if updateData:
                #     db_client.session.bulk_update_mappings(mapper=VariantValue, mappings=updateData)
                if data:
                    db_client.session.bulk_insert_mappings(mapper=VariantValue, mappings=data)
        except SQLAlchemyError as e:
            # error = str(e)
            db_client.session.rollback()
            db_client.session.flush()
            return map_sqlalchemy_error_to_http_status(e)
        success = False if error else True
        if success:
            message = "Records created Successfully"
        else:
            message = "There is an Error"
        return {
            'success': success,
            'message': message,
            'error': error,
        }


@variant_value_api_route.route('/<variant_value_id>/')
class EmployeeUpdateApi(Resource):
    @staticmethod
    def update_record(data, variant_value_id):
        start_time = datetime.datetime.now()
        compcode = request.args.get('current_user', {}).get('company_id')
        data.pop('variant_value_id', None)
        data["variant_value_temp"] = data.get("variant_value", "").replace(" ", "").lower()
        result = update_local(
            model=VariantValue,
            condition=VariantValue.variant_value_id == variant_value_id,
            values=data
        )
        if result.get('success'):
            redis_client.xadd(
                "variant_update_stream",
                {
                    "variant_value_id": variant_value_id,
                    "compcode": compcode
                }
            )

        # check_all_hash(variant_value_id=variant_value_id)
        # check_product_code_associated_to_variant_value(variant_value_id=variant_value_id)
        print("Time taken to update variant value:", (datetime.datetime.now() - start_time).total_seconds())
        return result

    @variant_value_api_route.marshal_with(get_variant_value_response)
    @login_required(permissions='variant-value.view')
    def get(self, variant_value_id):
        """
        Read user record / single record
        :param id:
        :return:
        """
        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id')
        query = text('''
        select variant_value.*,variant_attribute.variant_attribute_name from variant_value left join
         variant_attribute on variant_value.variant_attribute_id=variant_attribute.variant_attribute_id
         where variant_value.variant_value_id=:variant_value_id and variant_value.compcode=:compcode 
        ''')
        result = query_to_dict(db_client.engine.execute(query,compcode=compcode,variant_value_id=variant_value_id))
        return result[0]

    @variant_value_api_route.expect(update_variant_value_model)
    @variant_value_api_route.marshal_with(update_variant_value_response)
    @login_required(permissions='variant-value.edit')
    def put(self, variant_value_id):
        """
        Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, variant_value_id)
        return response

    @variant_value_api_route.expect(update_variant_value_model)
    @variant_value_api_route.marshal_with(update_variant_value_response)
    @login_required(permissions='variant-value.edit')
    def patch(self, variant_value_id):
        """
        Partial Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, variant_value_id)
        return response

    @variant_value_api_route.marshal_with(update_variant_value_response)
    @login_required(permissions='variant-value.delete')
    def delete(self, variant_value_id):
        """
        Soft delete VariantValue record
        TODO: Make soft delete
        :return:
        """

        result = ipss_db.update_record(
            model=VariantValue,
            condition=VariantValue.variant_value_id == variant_value_id,

            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result

######################################################################

    
    
