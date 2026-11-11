import datetime
from flask import request, session
from flask_restx import Resource
# from .. import ipss_db
from ipss_utils.ipss_api_doc import list_api_params, search_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, func, distinct, BigInteger
from sqlalchemy.exc import SQLAlchemyError

# from ..api_doc import product_group_attributes_groups_roles_fields
from ..models.productgroupattributesgroup import ProductGroupAttributesGroup
from ipss_utils.decorators import login_required

from ..routes.product_group_attributes_group import product_group_attributes_group_api_route, product_group_attributes_group_list_response, create_product_group_attributes_group_response,     update_product_group_attributes_group_model, update_product_group_attributes_group_response
# from sqlalchemy import and_, text
from ..routes.product_group_attributes_group import create_product_group_attributes_group_model, get_product_group_attributes_group_response,bulk_post_attribute_model
from .. import ipss_db, db_client

# Primary p_key name

primary_key = 'product_group_attributes_group_id'

from ..api_doc.product_group_atttribute_group_api_doc import search_filters
@product_group_attributes_group_api_route.route('/')
class ProductsApi(Resource):
    per_page = 20
    @product_group_attributes_group_api_route.marshal_with(product_group_attributes_group_list_response)
    @product_group_attributes_group_api_route.doc(params={**list_api_params,**search_filters})
    @login_required()
    def get(self):
        """
        List of product_group_attributes_group with pagination
        TODO: Search
        :return:
        """
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        sql_con = ''
        if request.args.get('product_group_attributes_group_id'):
            sql_con += ' and amd.product_group_attributes_group_id=:product_group_attributes_group_id '
        if request.args.get('product_group_id'):
            sql_con += ' and amd.product_group_id=:product_group_id '
        if request.args.get('attribute_group_id'):
            sql_con += ' and amd.attribute_group_id=:attribute_group_id '
        sql_query = text(f'''
               select pgag.*,ag.attribute_name,pg.group_name from product_group_attributes_group as pgag
               join attribute_group as ag on ag.attribute_group_id=amd.attribute_group_id
               join product_group pg on pg.product_group_id=pgag.product_group_id
               where amd.deleted is not true and amd.compcode=:ccode {sql_con}
               order by amd.attribute_meta_data_id desc
               limit :limit offset :offset
               ''')
        sql_query = query_to_dict(db_client.engine.execute(sql_query,
                                                           limit=results_per_page,
                                                           offset=offset,
                                                           ccode=ccode,
                                                           attribute_group_id=request.args.get('attribute_group_id'),
                                                           product_group_id=request.args.get(
                                                               'product_group_id'),
                                                           product_group_attributes_group_id=request.args.get('product_group_attributes_group_id')))
        sql_count = text(f'''
               select count(*)
               from product_group_attributes_group as pgag
               join attribute_group as ag on ag.attribute_group_id=amd.attribute_group_id
               join product_group pg on pg.product_group_id=pgag.product_group_id
               where amd.deleted is not true and amd.compcode=:ccode {sql_con}
               ''')
        sql_count = query_to_dict(db_client.engine.execute(sql_count,
                                                           ccode=ccode,
                                                           product_group_id=request.args.get(
                                                               'product_group_id'),
                                                           product_group_attributes_group_id=request.args.get(
                                                               'product_group_attributes_group_id'),
                                                           attribute_group_id=request.args.get('attribute_group_id')
                                                           ))
        return {
            "total_results": sql_count[0].get('count', 0) if len(sql_count) else 0,
            "page": paged,
            "results_per_page": results_per_page,
            "results": sql_query}
        # query = ProductGroupAttributesGroup.query.order_by(ProductGroupAttributesGroup.product_group_attributes_group_id.desc())
        # # Filtering by parent id (Primary Table ID)
        # # if request.args.get('product_group_attributes_group_id', None):
        # #     query = query.filter_by(product_group_attributes_group_id=request.args.get('product_group_attributes_group_id'))
        #
        # response = ipss_db.paginated_results(
        #     model=ProductGroupAttributesGroup,
        #     query=query,
        #     primary_key=primary_key
        # )
        # return response

    @login_required()
    @product_group_attributes_group_api_route.expect(bulk_post_attribute_model)
    @product_group_attributes_group_api_route.marshal_with(create_product_group_attributes_group_response)
    def post(self):
        """
        Create product_group_attributes_group record and return inserted id
        :return:
        """
        data = request.json
        data = data.get('data')
        compcode = request.args.get('current_user', {})
        cc = {"compcode": compcode.get('company_id'),
              "created_on": datetime.datetime.now(),
              "created_by": compcode.get('username')
              # "product_id": pkey if pkey else result.get('primary_key_id')[0]
              }
        updateData = [{**data.pop(i), **cc} for i in range(len(data) - 1, -1, -1) if
                      data[i].get('attribute_group_id')]
        data = [{**i, **cc} for i in data]
        error = ''
        try:
            with db_client.session.begin():
                if updateData:
                    db_client.session.bulk_update_mappings(mapper=ProductGroupAttributesGroup, mappings=updateData)
                if data:
                    db_client.session.bulk_insert_mappings(mapper=ProductGroupAttributesGroup, mappings=data)
        except SQLAlchemyError as e:
            error = str(e)
            db_client.session.rollback()
            db_client.session.flush()
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
        # data = request.json
        # # remove primary p_key if exists
        # data.pop(primary_key, None)
        # result = ipss_db.insert_record(
        #     model=product_group_attributes_group,
        #     values=data
        # )
        #
        # return ipss_db.created_response(
        #     result=result,
        #     message="Record has been created successfully",
        #     primary_key=primary_key
        # )


@product_group_attributes_group_api_route.route('/<product_group_attributes_group_id>/')
class EmployeeUpdateApi(Resource):
    @staticmethod
    def update_record(data, product_group_attributes_group_id):
        data.pop('product_group_attributes_group_id', None)

        result = ipss_db.update_record(
            model=ProductGroupAttributesGroup,
            condition=ProductGroupAttributesGroup.product_group_attributes_group_id == product_group_attributes_group_id,
            values=data
        )
        return result

    @product_group_attributes_group_api_route.marshal_with(get_product_group_attributes_group_response)
    @login_required()
    def get(self, product_group_attributes_group_id):
        """
        Read user record / single record
        :param id:
        :return:
        """

        user = ProductGroupAttributesGroup.query.filter_by(product_group_attributes_group_id=int(product_group_attributes_group_id)).first()
        return user

    @product_group_attributes_group_api_route.expect(update_product_group_attributes_group_model)
    @product_group_attributes_group_api_route.marshal_with(update_product_group_attributes_group_response)
    @login_required()
    def put(self, product_group_attributes_group_id):
        """
        Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, product_group_attributes_group_id)
        return response

    @product_group_attributes_group_api_route.expect(update_product_group_attributes_group_model)
    @product_group_attributes_group_api_route.marshal_with(update_product_group_attributes_group_response)
    @login_required()
    def patch(self, product_group_attributes_group_id):
        """
        Partial Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, product_group_attributes_group_id)
        return response

    @product_group_attributes_group_api_route.marshal_with(update_product_group_attributes_group_response)
    @login_required()
    def delete(self, product_group_attributes_group_id):
        """
        Soft delete product_group_attributes_group record
        TODO: Make soft delete
        :return:
        """

        result = ipss_db.update_record(
            model=ProductGroupAttributesGroup,
            condition=ProductGroupAttributesGroup.product_group_attributes_group_id == product_group_attributes_group_id,

            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result

######################################################################

    
    
