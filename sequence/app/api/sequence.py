import datetime

from flask_restx import Resource, abort
from flask import request, request_started
from ipss_utils.decorators import login_required
from ipss_utils.ipss_api_doc import list_api_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from .errorhandling import map_sqlalchemy_error_to_http_status, update_local
from .. import ipss_db, db_client
from ..redis_client.redis_client import redis_client
from ..routes.sequence import productGroupApiRoutes, postModel, listResponse, update_record_response_model
from ..api_doc import search_filters
from ..models.sequence import ProductSeq



@productGroupApiRoutes.route('/')
class Product(Resource):
    @login_required(permissions='product-sequence.list')
    @productGroupApiRoutes.marshal_with(listResponse)
    @productGroupApiRoutes.doc(params={**list_api_params, **search_filters})
    def get(self):
        current_user = request.args.get('current_user', {})
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        offset = (paged - 1) * results_per_page
        compcode = request.args.get('current_user', {}).get('company_id', None)
        sql_con = ''
        product_group_id = request.args.get('product_group_id')
        if product_group_id:
            sql_con = ' and product_group_id=:product_group_id '
        sql_query = text(f'''
                
select pgs.product_group_id,pg.group_name,
          JSON_AGG(
            JSON_BUILD_OBJECT(
                'id', pgs.product_group_seq_id,
                'rank', pgs.rank,
                'attribute_id', pgs.attribute_id,
                'product_group_seq_id', pgs.product_group_seq_id,
                'variant_attribute_name',
                CASE 
                    WHEN pgs.attribute_id = 0 THEN 'Product Name'
                    ELSE va.variant_attribute_name
                END,
                'isproduct', pgs.isproduct
            ) order by pgs.rank
        ) AS attributes
          from product_group_seq as pgs 
          left join variant_attribute as va on pgs.attribute_id = va.variant_attribute_id and va.deleted is not true
          left join product_group as pg on pg.product_group_id = pgs.product_group_id and pg.deleted is not true
          where pgs.deleted is not true  
          and pgs.compcode=:compcode {sql_con}
          group by pgs.product_group_id,pg.group_name
          order by pgs.product_group_id desc
        limit :limit offset :offset
            ''')
        sql_query = query_to_dict(db_client.engine.execute(sql_query, offset=offset,
                                                           limit=results_per_page,
                                                           product_group_id=product_group_id,
                                                           compcode=compcode
                                                           ))
        sql_count = text(f'''
        select count(distinct pgs.product_group_id)
          from product_group_seq as pgs 
          where pgs.deleted is not true  
          and pgs.compcode=:compcode {sql_con}
            ''')
        sql_count = query_to_dict(db_client.engine.execute(sql_count,
                                                           compcode=compcode,product_group_id=product_group_id))
        return {
            'total_results': sql_count[0].get('count') if sql_count else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'data': sql_query
        }


    @productGroupApiRoutes.expect(postModel)
    @login_required(permissions='product-sequence.add')
    def post(self):
        data=request.json

        product_group_id = data.get('product_group_id', None)
        items = data.get('attributes', None)
        error=''
        compcode = request.args.get('current_user', {})
        cc = {"compcode": compcode.get('company_id'),
              "created_on": datetime.datetime.now()
              }

        s = db_client.session
        try:
            with s.begin():
                if items:
                    itemdata = []
                    for i in items:
                        i.pop('product_group_seq_id', None)
                        i['product_group_id'] = product_group_id
                        itemdata.append({**i, **cc})
                    s.bulk_insert_mappings(mapper=ProductSeq, mappings=itemdata)

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
        }


@productGroupApiRoutes.route('/<product_group_id>/')
class ProductGroupUpdate(Resource):

    @staticmethod
    def put_method(data, product_group_id):
        items = data.pop('attributes', None)
        success = False
        error = ''
        try:
            with db_client.session.begin():
                current_user = request.args.get('current_user')
                compcode = current_user.get('company_id')
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
                    if item.get('product_group_seq_id'):
                        updateitemData.append({**item, **cc, 'deleted': False})
                        provided_ids.add(item.get('id'))
                    else:
                        itemdata.append({**item, **new_cc, "product_group_id": product_group_id, "deleted": False})

                print('providfe', provided_ids)

                existing_attributes = db_client.session.query(ProductSeq).filter(
                    ProductSeq.product_group_id == product_group_id,
                    ProductSeq.deleted != True
                ).all()

                existing_ids = {attr.product_group_seq_id for attr in existing_attributes}


                to_delete_ids = existing_ids - provided_ids

                print(to_delete_ids)

                if to_delete_ids:
                    db_client.session.query(ProductSeq).filter(
                        ProductSeq.product_group_seq_id.in_(to_delete_ids)
                    ).update({"deleted": True}, synchronize_session=False)

                if updateitemData:
                    print(updateitemData)
                    db_client.session.bulk_update_mappings(mapper=ProductSeq, mappings=updateitemData)
                if itemdata:
                    print(itemdata)
                    db_client.session.bulk_insert_mappings(mapper=ProductSeq, mappings=itemdata)

                redis_client.xadd(
                    "product_group_sequence_update_stream",
                    {
                        "product_group_id": product_group_id,
                        "compcode": compcode
                    }
                )

        except SQLAlchemyError as e:
            db_client.session.rollback()
            return map_sqlalchemy_error_to_http_status(e)


        return {
            'success': True,
            'message': "Update successful"
        }

    @staticmethod
    def update_method(data, product_group_id):
        data.pop('id', None)
        result = update_local(
            model=ProductSeq,
            condition=ProductSeq.product_group_id == product_group_id,
            values=data
        )
        return result

    @productGroupApiRoutes.marshal_with(postModel)
    # @login_required(permissions='product_stages_mapping.view')
    @login_required(permissions='product-sequence.view')
    def get(self, product_group_id):
        """
        Read user record / single record
        :param id:
        :return:
        """
        user = ProductSeq.query.filter_by(id=int(product_group_id)).all()
        return user

    @productGroupApiRoutes.expect(postModel)
    @productGroupApiRoutes.marshal_with(update_record_response_model)
    # @login_required(permissions='product_stages_mapping.edit')
    @login_required(permissions='product-sequence.edit')
    def put(self, product_group_id):
        """
        Update Employees record
        :return:
        """
        data = request.json
        response = self.put_method(data, product_group_id)
        return response

    @productGroupApiRoutes.expect(postModel)
    @productGroupApiRoutes.marshal_with(update_record_response_model)
    # @login_required(permissions='product_stages_mapping.edit')
    @login_required(permissions='product-sequence.edit')
    def patch(self, product_id):
        """
        Partial Update Employees record
        :return:
        """
        data = request.json
        response = self.update_method(data, product_id)
        return response

    @productGroupApiRoutes.marshal_with(update_record_response_model)
    # @login_required(permissions='product_stages_mapping.delete')
    @login_required(permissions='product-sequence.delete')
    def delete(self, product_group_id):
        """
        Soft delete ProdStages record
        TODO: Make soft delete
        :return:
        """
        result = update_local(
            model=ProductSeq,
            condition=ProductSeq.product_group_id == product_group_id,
            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result

######################################################################




