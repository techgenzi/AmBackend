import datetime
from flask import request, session
from flask_restx import Resource
# from .. import ipss_db
from ipss_utils.ipss_api_doc import list_api_params, search_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, func, distinct, BigInteger
# from ..api_doc import job_dc_orders_roles_fields
from ..models.orders_items import JoPoLineItems
from ipss_utils.decorators import login_required

from ..routes.orders_items import job_dc_order_api_route, job_dc_order_list_response, create_job_dc_order_response,     update_job_dc_order_model, update_job_dc_order_response
# from sqlalchemy import and_, text
from ..routes.orders_items import create_job_dc_order_model, get_job_dc_order_response
from .. import ipss_db, db_client

# Primary p_key name

primary_key = 'id'


@job_dc_order_api_route.route('/')
class JoPoLineItemsApi(Resource):
    per_page = 20
    @job_dc_order_api_route.marshal_with(job_dc_order_list_response)
    @job_dc_order_api_route.doc(params=list_api_params)
    @login_required()
    def get(self):
        """
        List of job_dc_order with pagination
        TODO: Search
        :return:
        """
        query = JoPoLineItems.query.order_by(JoPoLineItems.id.desc())
        # Filtering by parent id (Primary Table ID)
        # if request.args.get('id', None):
        #     query = query.filter_by(id=request.args.get('id'))

        response = ipss_db.paginated_results(
            model=JoPoLineItems,
            query=query,
            primary_key=primary_key
        )
        return response

    @login_required()
    @job_dc_order_api_route.expect(create_job_dc_order_model)
    @job_dc_order_api_route.marshal_with(create_job_dc_order_response)
    def post(self):
        """
        Create job_dc_order record and return inserted id
        :return:
        """
        data = request.json
        # remove primary p_key if exists
        data.pop(primary_key, None)
        result = ipss_db.insert_record(
            model=JoPoLineItems,
            values=data
        )

        return ipss_db.created_response(
            result=result,
            message="Record has been created successfully",
            primary_key=primary_key
        )


@job_dc_order_api_route.route('/<id>/')
class EmployeeUpdateApi(Resource):
    @staticmethod
    def update_record(data, id):
        data.pop('id', None)

        result = ipss_db.update_record(
            model=JoPoLineItems,
            condition=JoPoLineItems.id == id,
            values=data
        )
        return result

    @job_dc_order_api_route.marshal_with(get_job_dc_order_response)
    @login_required()
    def get(self, id):
        """
        Read user record / single record
        :param id:
        :return:
        """

        user = JoPoLineItems.query.filter_by(id=int(id)).first()
        return user

    @job_dc_order_api_route.expect(update_job_dc_order_model)
    @job_dc_order_api_route.marshal_with(update_job_dc_order_response)
    @login_required()
    def put(self, id):
        """
        Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, id)
        return response

    @job_dc_order_api_route.expect(update_job_dc_order_model)
    @job_dc_order_api_route.marshal_with(update_job_dc_order_response)
    @login_required()
    def patch(self, id):
        """
        Partial Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, id)
        return response

    @job_dc_order_api_route.marshal_with(update_job_dc_order_response)
    @login_required()
    def delete(self, id):
        """
        Soft delete JoPoLineItems record
        TODO: Make soft delete
        :return:
        """

        result = ipss_db.update_record(
            model=JoPoLineItems,
            condition=JoPoLineItems.id == id,

            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result

######################################################################

    
    
