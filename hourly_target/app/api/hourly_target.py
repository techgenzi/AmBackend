import datetime
from flask import request, session
from flask_restx import Resource
# from .. import ipss_db
from ipss_utils.ipss_api_doc import list_api_params, search_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, func, distinct, BigInteger, and_
from sqlalchemy.exc import SQLAlchemyError

# from ..api_doc import hourly_targets_roles_fields
from ..models.hourly_target import HourlyTarget
from ipss_utils.decorators import login_required

from ..routes.hourly_target import hourly_target_api_route, hourly_target_list_response, create_hourly_target_response, \
    update_hourly_target_model, update_hourly_target_response, bulk_hourly_model
# from sqlalchemy import and_, text
from ..routes.hourly_target import create_hourly_target_model, get_hourly_target_response
from .. import ipss_db, db_client
from ..api_doc import search_filters
from .errorhandling import map_sqlalchemy_error_to_http_status
# Primary p_key name

primary_key = 'hourly_target_id'


@hourly_target_api_route.route('/')
class HourlyTargetApi(Resource):
    per_page = 20
    @hourly_target_api_route.marshal_with(hourly_target_list_response)
    @hourly_target_api_route.doc(params={**list_api_params,**search_filters})
    @login_required()
    def get(self):
        """
        List of hourly_target with pagination
        TODO: Search
        :return:
        """
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        page = int(request.args.get('paged')) if request.args.get('paged') else 1
        result_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (page - 1) * result_per_page if (page - 1) * result_per_page else 0
        sql_con=''
        if request.args.get('hourly_target_id'):
            sql_con+=' and ht.hourly_target_id=:hourly_target_id '
        if request.args.get('plan_id'):
            sql_con+=' and ht.plan_id=:plan_id '
        result=text(f'''
        select ht.*,pp.plan_unique from hourly_target ht
        join production_plan pp on ht.plan_id=pp.production_plan_id 
        where ht.compcode=:ccode and ht.deleted is not true {sql_con}
        order by hourly_target_id desc
        limit :limit offset :offset
        ''')
        result=query_to_dict(db_client.engine.execute(result,ccode=ccode,
                                                      plan_id=request.args.get('plan_id'),
                                                      hourly_target_id=request.args.get('hourly_target_id'),
                                                      limit=result_per_page,offset=offset))
        sql_count=text(f''' select count(*)
        from hourly_target ht
        join production_plan pp on ht.plan_id=pp.production_plan_id 
        where ht.compcode=:ccode and ht.deleted is not true {sql_con}
        ''')
        sql_count=query_to_dict(db_client.engine.execute(sql_count,ccode=ccode,
                                                         plan_id=request.args.get('plan_id'),
                                                         hourly_target_id=request.args.get('hourly_target_id'),
                                                         ))
        return {
            "total_results": sql_count[0].get('count', 0) if len(sql_count) else 0,
            "page": page,
            "results_per_page": result_per_page,
            "results": result
        }
        # query = HourlyTarget.query.order_by(HourlyTarget.hourly_target_id.desc())
        # # Filtering by parent id (Primary Table ID)
        # # if request.args.get('hourly_target_id', None):
        # #     query = query.filter_by(hourly_target_id=request.args.get('hourly_target_id'))
        #
        # response = ipss_db.paginated_results(
        #     model=HourlyTarget,
        #     query=query,
        #     primary_key=primary_key
        # )
        # return response

    @login_required()
    @hourly_target_api_route.expect(bulk_hourly_model)
    @hourly_target_api_route.marshal_with(create_hourly_target_response)
    def post(self):
        """
        Create hourly_target record and return inserted id
        :return:
        """
        data = request.json
        data = data.get('data', None)
        compcode = request.args.get('current_user', {})
        cc = {"compcode": compcode.get('company_id'),
              "created_on": str(datetime.datetime.now()),
              # "product_id": pkey if pkey else result.get('primary_key_id')[0]
              }
        total_count = db_client.session.query(func.count(HourlyTarget.hourly_target_id)) \
                          .filter(and_(
                                       HourlyTarget.compcode == compcode.get('company_id'))) \
                          .scalar() + 1
        # updateData = [{**data.pop(i), **cc} for i in range(len(data) - 1, -1, -1) if
        #               data[i].get('hourly_target_id')]
        updateData = []
        for i in range(len(data) - 1, -1, -1):
            if data[i].get('hourly_target_id'):
                new_dict = {**data.pop(i), **cc,**{"doc_id":total_count}}
                updateData.append(new_dict)
                total_count+=1
        data = [{**i, **cc} for i in data]
        error = ''
        message = None
        try:
            with db_client.session.begin():

                if updateData:
                    db_client.session.bulk_update_mappings(mapper=HourlyTarget, mappings=updateData)
                if data:
                    db_client.session.bulk_insert_mappings(mapper=HourlyTarget, mappings=data)
        except SQLAlchemyError as e:
            # error = str(e)
            db_client.session.rollback()
            db_client.session.flush()

            res = map_sqlalchemy_error_to_http_status(e)
            return res
        success = False if error else True
        if success:
            message = "Records created Successfully"
        return {
            'success': success,
            'message': message,
            'error': error,
        }

@hourly_target_api_route.route('/<hourly_target_id>/')
class EmployeeUpdateApi(Resource):
    @staticmethod
    def update_record(data, hourly_target_id):
        data.pop('hourly_target_id', None)

        result = ipss_db.update_record(
            model=HourlyTarget,
            condition=HourlyTarget.hourly_target_id == hourly_target_id,
            values=data
        )
        return result

    @hourly_target_api_route.marshal_with(get_hourly_target_response)
    @login_required()
    def get(self, hourly_target_id):
        """
        Read user record / single record
        :param id:
        :return:
        """

        user = HourlyTarget.query.filter_by(hourly_target_id=int(hourly_target_id)).first()
        return user

    @hourly_target_api_route.expect(update_hourly_target_model)
    @hourly_target_api_route.marshal_with(update_hourly_target_response)
    @login_required()
    def put(self, hourly_target_id):
        """
        Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, hourly_target_id)
        return response

    @hourly_target_api_route.expect(update_hourly_target_model)
    @hourly_target_api_route.marshal_with(update_hourly_target_response)
    @login_required()
    def patch(self, hourly_target_id):
        """
        Partial Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, hourly_target_id)
        return response

    @hourly_target_api_route.marshal_with(update_hourly_target_response)
    @login_required()
    def delete(self, hourly_target_id):
        """
        Soft delete HourlyTarget record
        TODO: Make soft delete
        :return:
        """

        result = ipss_db.update_record(
            model=HourlyTarget,
            condition=HourlyTarget.hourly_target_id == hourly_target_id,

            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result

######################################################################

    
    
