import datetime

from flask import request, session
from flask_restx import Resource, abort
# from .. import ipss_db
from ipss_utils.ipss_api_doc import list_api_params, search_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, func, distinct, BigInteger, bindparam, NUMERIC, Boolean, insert, update
from sqlalchemy.exc import SQLAlchemyError

from .errorhandling import map_sqlalchemy_error_to_http_status, update_local, sequence
from ..api_doc import search_filter
from ..models.cost_estimation import Estimation, EstimationProduct
from ipss_utils.decorators import login_required

from ..routes.cost_estimation import cost_estimation_api_route, estimation_post_model, estimation_list_response
from .. import ipss_db, db_client




@cost_estimation_api_route.route('/')
class CostEstimationApi(Resource):

    @cost_estimation_api_route.marshal_with(estimation_list_response)
    @cost_estimation_api_route.doc(params={**list_api_params,**search_filter})
    @login_required(permission='cost_estimation.list')
    # @login_required()
    def get(self):
        """
        List of prod_stages with pagination
        TODO: Search
        :return:
        """
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page', '20'))
        offset = (paged - 1) * results_per_page
        compcode = request.args.get('current_user', {}).get('company_id')
        cost_estimation_id = request.args.get('cost_estimation_id', None)
        estimation_product_id = request.args.get('estimation_product_id', None)
        sql_condition = ""

        if cost_estimation_id:
            sql_condition += ' and ce.cost_estimation_id=:cost_estimation_id '
        if estimation_product_id:
            sql_condition += ' and ep.estimation_product_id=:estimation_product_id '
        sql_query = text(f'''
            select ce.cost_estimation_id,ce.estimation_code,ce.customer_id,ce.marketing_person,
            ce.estimate_date,ce.description,v.companyname,v.emailid,v.mobileno,
            json_agg(
            json_build_object(
            'estimation_product_id',ep.estimation_product_id,
                'cost_estimation_id',ep.cost_estimation_id,
                'product_id',ep.product_id,
                'product_code', p.product_code,
                'sku_id', p.sku_id,
                'uom', u.uom,
                'admin_cost',ep.admin_cost,
                'margin_cost',ep.margin_cost,
                'transport_cost_per_piece',ep.transport_cost_per_piece,
                'quantity',ep.quantity,
                'material_cost',ep.material_cost,
                'labour_cost',ep.labour_cost,
                'packing_material_cost',ep.packing_material_cost,
                'eto_cost', ep.eto_cost,
                'miscellaneous_cost' , ep.miscellaneous_cost,
                'cost_definition', ep.cost_definition,
                'final_cost', ep.final_cost,
                'description', ep.description
            )
            ) as data
            from cost_estimation as ce 
            left join estimation_product as ep on ce.cost_estimation_id = ep.cost_estimation_id
            left join vendor as v on v.vendorid = ce.customer_id
            left join products as p on ep.product_id = p.product_id
            left join uom as u on p.uom_id = u.id
            where ce.deleted is not true and ep.deleted is not true and ce.compcode =:compcode {sql_condition}
            group by ce.cost_estimation_id,ce.estimation_code,ce.customer_id,ce.marketing_person,
            ce.estimate_date,ce.description,v.companyname,v.emailid,v.mobileno
            order by ce.cost_estimation_id desc
            limit :limit offset :offset
        ''')
        result = query_to_dict(db_client.engine.execute(sql_query,
                                                           compcode=compcode,
                                                           limit=results_per_page,
                                                           offset=offset,
                                                            estimation_product_id=estimation_product_id,
                                                        cost_estimation_id=cost_estimation_id
                                                           ))
        sql_count = text(f'''
            select count(ce.cost_estimation_id)
            from cost_estimation as ce 
            left join estimation_product as ep on ce.cost_estimation_id = ep.cost_estimation_id
            where ce.deleted is not true and ep.deleted is not true and ce.compcode =:compcode {sql_condition}
        ''')
        sql_count = query_to_dict(db_client.engine.execute(sql_count,
                                                           compcode=compcode,
                                                           estimation_product_id=estimation_product_id,
                                                           cost_estimation_id=cost_estimation_id))

        return {

            'total_results': sql_count[0].get('count') if sql_count else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': result
        }

    @cost_estimation_api_route.expect(estimation_post_model)
    @login_required(permissions='cost_estimation.add')
    def post(self):
        """
        Create prod_stages record and return inserted id
        :return:
        """
        data = request.json
        compcode = request.args.get('current_user', {})
        cc = {"compcode": compcode.get('company_id'),
              "created_on": datetime.datetime.now()
              }
        error = ''
        items = data.pop('data', None)
        success = False
        s = db_client.session
        try:
            with s.begin():
                seq = sequence(table='cost_estimation', compcode=compcode.get('company_id'), prefix='EST-', lastno=0, zeropadding=6)
                data['estimation_code'] = seq
                stmt = insert(Estimation).values(**data, **cc).returning(Estimation.cost_estimation_id)
                result = s.execute(stmt)
                primary_key_id = result.scalar()
                if items:
                    itemdata = []
                    for i in items:
                        i.pop('estimation_product_id', None)
                        i['cost_estimation_id'] = primary_key_id
                        itemdata.append({**i, **cc})
                    s.bulk_insert_mappings(mapper=EstimationProduct, mappings=itemdata)
            success = True

        except SQLAlchemyError as e:
            s.flush()
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)
        if success:
            message = "Records created Successfully"
        else:
            message = "There is an Error"
        return {
            'success': success,
            'message': message,
            'error': error,
            'inserted_id': primary_key_id
        }


@cost_estimation_api_route.route('/<cost_estimation_id>')
class CostEstimationProductApi(Resource):

    @login_required(permissions='cost_estimation.edit')
    def put(self, cost_estimation_id):
        data = request.json
        items = data.pop('data', None)
        compcode = request.args.get('current_user', {})
        cc = {"compcode": compcode.get('company_id'),
              "created_on": datetime.datetime.now()
              }
        s = db_client.session
        try:
            stmt = (
                update(Estimation)
                .where(Estimation.cost_estimation_id == cost_estimation_id)
                .values(**data)
            )
            s.execute(stmt)

            if items:
                update_data = []
                insert_data = []
                for i in items:
                    if i.get('estimation_product_id'):
                        update_data.append(i)
                    else:
                        insert_data.append({**i, **cc, 'cost_estimation_id': cost_estimation_id})

                s.bulk_insert_mappings(mapper=EstimationProduct, mappings=insert_data)
                s.bulk_update_mappings(mapper=EstimationProduct, mappings=update_data)
                s.commit()

        except Exception as e:
            s.flush()
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'message': 'update succesfully'
        }

    @login_required(permissions='cost_estimation.delete')
    def delete(self, cost_estimation_id):

        res = update_local(model=EstimationProduct,
                     condition=EstimationProduct.cost_estimation_id==cost_estimation_id,
                     values={
                         'deleted': True,
                         'deleted_at': datetime.datetime.now()
                     })

        return res


@cost_estimation_api_route.route('/estimation_product_id/<estimation_product_id>')
class CostEstimationDelete(Resource):

    @login_required(permissions='cost_estimation.delete')
    def delete(self, estimation_product_id):
        res = update_local(model=EstimationProduct,
                     condition=EstimationProduct.estimation_product_id == estimation_product_id,
                     values={
                         'deleted': True,
                         'deleted_at': datetime.datetime.now()
                     })

        return res

######################################################################
