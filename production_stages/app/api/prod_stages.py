import datetime

from flask import request, session
from flask_restx import Resource, abort
# from .. import ipss_db
from ipss_utils.ipss_api_doc import list_api_params, search_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, func, distinct, BigInteger, bindparam, NUMERIC, Boolean
from sqlalchemy.exc import SQLAlchemyError

from .errorhandling import map_sqlalchemy_error_to_http_status, update_local
from ..api_doc import search_fields
# from ..api_doc import prod_stagess_roles_fields
from ..models.prod_stages import ProdStages
from ipss_utils.decorators import login_required

from ..routes.prod_stages import prod_stages_api_route, prod_stages_list_response, create_prod_stages_response, \
    update_prod_stages_model, update_prod_stages_response, prod_stages_model, det_model, config_resposne, stages_mode
# from sqlalchemy import and_, text
from ..routes.prod_stages import create_prod_stages_model, get_prod_stages_response
from .. import ipss_db, db_client
from .helper import post_query
# Primary p_key name

primary_key = 'id'


@prod_stages_api_route.route('/')
class ProdStagesApi(Resource):
    per_page = 20

    @prod_stages_api_route.marshal_with(prod_stages_list_response)
    @prod_stages_api_route.doc(params={**search_fields, **list_api_params})
    # @user_verify(permission='product_satges_mapping.list', db_client=db_client)
    # @login_required(permissions='product_satges_mapping.list||product_stages_mapping.view||product_stages_mapping.edit||'
    #                             'product_stages_mapping.delete')
    @login_required(permission='product_stages_mapping.list')
    # @login_required()
    def get(self):
        """
        List of prod_stages with pagination
        TODO: Search
        :return:
        """
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        compcode = request.args.get('current_user', {}).get('company_id')
        sql_condition = ""
        con1 = ''
        if request.args.get('product_id'):
            sql_condition += ' and ps.product_id =:product_id '
            # con1 += ' and ps.product_id=:product_id '
        if request.args.get('id'):
            sql_condition += ' and ps.id =:id '
        sql_query=text(f'''
        with stg as(
        select s.stage_name,s.stage_id,p.product_id,p.product_code,p.product_name,p.sku_id,ps.rank_id,ps.id,
        ps.required_quantity_per_unit,
        json_agg(json_build_object(
        'activity_stage_map_id',asm.activity_stage_map_id,
        'config_id',asm.config_id,
        'config_name',cm.process_name,
        'production_stage_id',asm.production_stage_id,
        'target_per_hour',asm.target_per_hour,
        'is_final_process',asm.is_final_process
        ) order by asm.activity_stage_map_id asc) FILTER (WHERE asm.activity_stage_map_id IS NOT NULL) AS activities
        from production_stages ps 
        join stage s on s.stage_id =ps.stage_id 
        join products p on p.product_id=ps.product_id
        left join activity_stage_map as asm on asm.production_stage_id=ps.id and asm.deleted is not true
        left join process_config as cm on cm.process_id=asm.config_id and cm.deleted is not true
        where ps.deleted is not true and s.deleted is not true and p.deleted is not true and
        asm.deleted is not true and cm.deleted is not true and ps.compcode=:ccode {sql_condition}
        group by s.stage_name,s.stage_id,p.product_id,p.product_code,p.product_name,p.sku_id,ps.rank_id,ps.id
        )
        select stg.product_id,stg.product_code,stg.product_name,stg.sku_id,
        json_agg(json_build_object(
        'stage_name',stg.stage_name,
        'stage_id',stg.stage_id,
        'required_quantity_per_unit',coalesce (stg.required_quantity_per_unit,0),
        'rank_id',stg.rank_id,
        'id',stg.id,
        'activities',coalesce (stg.activities,'[]')
        )order by stg.rank_id asc) stages
        from stg
        group by stg.product_id,stg.product_code,stg.product_name,stg.sku_id
        limit :limit offset :offset
        ''')
        sql_query=query_to_dict(db_client.engine.execute(sql_query,
                                                         ccode=compcode,
                                                         limit=results_per_page,
                                                         id=request.args.get('id'),
                                                         product_id=request.args.get('product_id'),
                                                         offset=offset))
        sql_count=text(f'''
        select count(distinct p.product_id)
        from production_stages ps 
        join stage s on s.stage_id =ps.stage_id 
        join products p on p.product_id=ps.product_id
        left join activity_stage_map as asm on asm.production_stage_id=ps.id and asm.deleted is not true
        left join process_config as cm on cm.process_id=asm.config_id and cm.deleted is not true
        where ps.deleted is not true and s.deleted is not true and p.deleted is not true and
        asm.deleted is not true and cm.deleted is not true and ps.compcode=:ccode {sql_condition}
        ''')
        sql_count=query_to_dict(db_client.engine.execute(sql_count,
                                                         ccode=compcode,
                                                         limit=results_per_page,
                                                         id=request.args.get('id'),
                                                         product_id=request.args.get('product_id'),
                                                         offset=offset
                                                         ))
        return {
            'total_results': sql_count[0].get('count') if sql_count else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': sql_query
        }

    # @login_required(permissions='product_stages_mapping.add')
    @prod_stages_api_route.expect(prod_stages_model)
    @prod_stages_api_route.marshal_with(create_prod_stages_response)
    @login_required(permission='product_stages_mapping.add')
    # @login_required()
    def post(self):
        """
        Create prod_stages record and return inserted id
        :return:
        """
        return post_query()
        # data = request.json
        # items = data.pop('stages', None)
        # product_id = data.pop('product_id', None)
        # compcode = request.args.get('current_user', {})
        # cc = {"compcode": compcode.get('company_id'),
        #       "created_on": datetime.datetime.now()
        #       }
        # error = ''
        # success = False
        # s = db_client.session
        # try:
        #     with s.begin():
        #         if items:
        #             itemdata = []
        #             for i in items:
        #                 i.pop('id', None)
        #                 i['product_id'] = product_id
        #                 activities = i.pop('activities', None)
        #                 if activities:
        #                     for j in activities:
        #                         itemdata.append({**i, **cc, 'activity_config_id': j.get('activity_config_id'), 'target_per_hour': j.get('target_per_hour')})
        #                 else:
        #                     itemdata.append({**i, **cc})
        #             s.bulk_insert_mappings(mapper=ProdStages, mappings=itemdata)
        #     success = True
        #
        # except SQLAlchemyError as e:
        #     s.flush()
        #     s.rollback()
        #     # raise Exception(e)
        #     return map_sqlalchemy_error_to_http_status(e)
        # if success:
        #     message = "Records created Successfully"
        # else:
        #     message = "There is an Error"
        # return {
        #     'success': success,
        #     'message': message,
        #     'error': error,
        # }


@prod_stages_api_route.route('/<product_id>/')
class EmployeeUpdateApi(Resource):

    @staticmethod
    def put_method(data, product_id):
        items = data.pop('stages', None)
        success = False
        error = ''
        try:
            with db_client.session.begin():
                # curr = request.args.get('current_user', {})
                # compcode = curr.get('company_id', None)
                current_user = request.args.get('current_user')
                compcode = current_user.get('company_id')
                print(compcode,"FGu")
                print(current_user,"FG")
                cc = {
                    "compcode": compcode,
                    "modified_on": datetime.datetime.now()
                }
                new_cc = {
                    "compcode": compcode,
                    "created_on": datetime.datetime.now()
                }
                updateitemData = []
                itemdata = []
                provided_ids = set()
                for item in items:
                    if item.get('id'):
                        updateitemData.append({**item, **cc, 'deleted': False})
                        provided_ids.add(item.get('id'))
                    else:
                        itemdata.append({**item, **new_cc, "product_id": product_id, "deleted": False})

                print('providfe', provided_ids)

                existing_attributes = db_client.session.query(ProdStages).filter(
                    ProdStages.product_id == product_id,
                    ProdStages.deleted != True
                ).all()

                existing_ids = {attr.id for attr in existing_attributes}


                to_delete_ids = existing_ids - provided_ids

                print(to_delete_ids)

                if to_delete_ids:
                    db_client.session.query(ProdStages).filter(
                        ProdStages.id.in_(to_delete_ids)
                    ).update({"deleted": True}, synchronize_session=False)

                if updateitemData:
                    print(updateitemData)
                    db_client.session.bulk_update_mappings(mapper=ProdStages, mappings=updateitemData)
                if itemdata:
                    print(itemdata)
                    db_client.session.bulk_insert_mappings(mapper=ProdStages, mappings=itemdata)

                success = True

        except SQLAlchemyError as e:
            db_client.session.rollback()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': success,
            'message': "Update successful" if success else "Error in update",
            'error': error
        }

    @staticmethod
    def update_method(data, product_id):
        data.pop('id', None)
        result = update_local(
            model=ProdStages,
            condition=ProdStages.product_id == product_id,
            values=data
        )
        return result

    @prod_stages_api_route.marshal_with(stages_mode)
    @login_required(permissions='product_stages_mapping.view')
    # @login_required()
    def get(self, product_id):
        """
        Read user record / single record
        :param id:
        :return:
        """
        user = ProdStages.query.filter_by(id=int(product_id)).first()
        return user

    @prod_stages_api_route.expect(prod_stages_model)
    @prod_stages_api_route.marshal_with(update_prod_stages_response)
    @login_required(permissions='product_stages_mapping.edit')
    # @login_required()
    def put(self, product_id):
        """
        Update Employees record
        :return:
        """
        data = request.json
        response = self.put_method(data, product_id)
        return response

    @prod_stages_api_route.expect(stages_mode)
    @prod_stages_api_route.marshal_with(update_prod_stages_response)
    @login_required(permissions='product_stages_mapping.edit')
    # @login_required()
    def patch(self, product_id):
        """
        Partial Update Employees record
        :return:
        """
        data = request.json
        response = self.update_method(data, product_id)
        return response

    @prod_stages_api_route.marshal_with(update_prod_stages_response)
    @login_required(permissions='product_stages_mapping.delete')
    # @login_required()
    def delete(self, product_id):
        """
        Soft delete ProdStages record
        TODO: Make soft delete
        :return:
        """
        result = update_local(
            model=ProdStages,
            condition=ProdStages.product_id == product_id,
            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result

######################################################################
@prod_stages_api_route.route('/production_stage/<id>/')
class EmployeeUpdateApi(Resource):
    @prod_stages_api_route.marshal_with(update_prod_stages_response)
    @login_required(permissions='product_stages_mapping.delete')
    # @login_required()
    def delete(self, id):
        """
        Soft delete ProdStages record
        TODO: Make soft delete
        :return:
        """
        result = update_local(
            model=ProdStages,
            condition=ProdStages.id == id,
            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result