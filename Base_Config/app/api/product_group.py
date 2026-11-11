import datetime
from collections import defaultdict

from flask import request, session
from flask_restx import Resource
# from .. import ipss_db
from ipss_utils.ipss_api_doc import list_api_params, search_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, func, distinct, BigInteger, insert, update
from sqlalchemy.exc import SQLAlchemyError

# from ..api_doc import product_groups_roles_fields
from ..models.product_group import ProductGroup, ProductGroupAttribute
from ipss_utils.decorators import login_required

from ..routes.product_group import product_group_api_route, product_group_list_response, create_product_group_response, \
    update_product_group_model, update_product_group_response, bulk_model, bulk_model_get
# from sqlalchemy import and_, text
from ..routes.product_group import create_product_group_model, get_product_group_response
from .. import ipss_db, db_client
# Primary p_key name
from .errorhandling import map_sqlalchemy_error_to_http_status,update_local
primary_key = 'product_group_id'


@product_group_api_route.route('/')
class ProductGroupApi(Resource):
    per_page = 20
    @product_group_api_route.marshal_with(bulk_model_get)
    @product_group_api_route.doc(params=list_api_params)
    @login_required()
    def get(self):
        """
        List of product_group with pagination
        TODO: Search
        :return:
        """
        curr = request.args.get('current_user', {})
        compcode = curr.get('company_id', None)
        result_per_page = request.args.get('results_per_page', 20)
        page = request.args.get("page", 1)
        offset = (page - 1) * result_per_page if (page - 1) * result_per_page else 0

        query = text('''
                        SELECT 
                    pg.product_group_id,
                    pg.group_name,
                    pg.description,
                    COALESCE(
                        JSONB_AGG(
                            CASE 
                                WHEN pga.product_group_attribute_id IS NOT NULL THEN 
                                    JSONB_BUILD_OBJECT(
                                        'product_group_attribute_id', pga.product_group_attribute_id,
                                        'product_group_id', pga.product_group_id,
                                        'attribute_id', COALESCE(pga.attribute_id, 0),
                                        'variant_attribute_name', va.variant_attribute_name,
                                        'deleted', pga.deleted::TEXT
                                    )
                                ELSE NULL
                            END
                        ) FILTER (WHERE pga.product_group_attribute_id IS NOT NULL), '[]'::JSONB
                    ) AS data
                FROM product_group AS pg
                LEFT JOIN product_group_attribute AS pga 
                    ON pg.product_group_id = pga.product_group_id 
                    AND pga.deleted IS NOT TRUE
                LEFT JOIN variant_attribute AS va 
                    ON pga.attribute_id = va.variant_attribute_id
                WHERE pg.deleted IS NOT TRUE 
                    AND pg.compcode = :compcode
                GROUP BY pg.product_group_id, pg.group_name, pg.description
                ORDER BY pg.created_on DESC
                LIMIT :limit OFFSET :offset;
        ''')
        result = query_to_dict(db_client.engine.execute(query,compcode=compcode, limit=result_per_page,offset=offset))
        query_count = text('''
        select count(pg.product_group_id)
         from product_group as pg 
        where pg.deleted is not true and pg.compcode = :compcode
        ''')
        print(result,"ert")
        count = query_to_dict(db_client.engine.execute(query_count,compcode=compcode, limit=result_per_page, offset=offset))
        print(count)

        return {
            'total_results': count[0].get('count', None) if count else 0,
            'page': page,
            'results_per_page': result_per_page,
            "results": result
        }

    @login_required(permissions='product-group.add')
    @product_group_api_route.expect(bulk_model)
    @product_group_api_route.marshal_with(create_product_group_response)
    def post(self):
        """
        Create product_group record and return inserted id
        :return:
        """
        data = request.json
        items = data.pop('data', None)
        itemsdata = None
        data.pop('product_group_id', None)
        compcode = request.args.get('current_user', {})
        cc = {"compcode": compcode.get('company_id'),
              "created_on": datetime.datetime.now(),
              "created_by": compcode.get('username')
              }
        if items:
            itemdata = [{**i, **cc} for i in items]
        error = ''
        success = False
        s = db_client.session
        try:
            with s.begin():
                stmt = (
                    insert(ProductGroup).values(**data,**cc).returning(ProductGroup.product_group_id)
                )
                result = s.execute(stmt)
                primary_key_id = result.scalar()
                print('wer',primary_key_id)
                if primary_key_id:
                    if items:
                        itemdata = [{**i, **{"product_group_id": primary_key_id}} for i in itemdata]
                        s.bulk_insert_mappings(mapper=ProductGroupAttribute, mappings=itemdata)

                success = True

        except SQLAlchemyError as e:
            error = str(e)
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


@product_group_api_route.route('/<product_group_id>/')
class EmployeeUpdateApi(Resource):
    @staticmethod
    def update_record(data, product_group_id):
        data.pop('product_group_id', None)
        items = data.pop('data', None)
        success = False
        error = ''

        try:
            with db_client.session.begin():
                # Update ProductGroup
                stmt = (
                    update(ProductGroup)
                    .where(ProductGroup.product_group_id == product_group_id)
                    .values(**data)
                )
                db_client.session.execute(stmt)

                # Prepare common fields
                compcode = request.args.get('current_user', {})
                cc = {
                    "compcode": compcode.get('company_id'),
                    "modified_on": datetime.datetime.now()
                }
                new_cc = {
                    "compcode": compcode.get('company_id'),
                    "created_on": datetime.datetime.now()
                }

                # Prepare data for updating and inserting
                updateitemData = [
                    {**items.pop(i), **cc} for i in range(len(items) - 1, -1, -1)
                    if items[i].get('product_group_attribute_id')
                ]
                itemdata = [
                    {**i, **new_cc, **{"product_group_id": product_group_id}} for i in items
                ]

                # Adjust 'deleted' flag if necessary
                for i in updateitemData:
                    if i.get('deleted', '').lower() == 'true':
                        i['deleted'] = True

                # Perform bulk update and insert if data is present
                if updateitemData:
                    db_client.session.bulk_update_mappings(ProductGroupAttribute, updateitemData)
                if itemdata:
                    db_client.session.bulk_insert_mappings(ProductGroupAttribute, itemdata)

                success = True

        except SQLAlchemyError as e:
            # Roll back transaction on error
            error = f"Database error: {str(e)}"
            db_client.session.rollback()  # Ensure rollback happens outside of 'begin' context
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': success,
            'message': "Update successful" if success else "Error in update",
            'error': error
        }

    @staticmethod
    def put_record(data, product_group_id):
        data.pop('product_group_id', None)
        product_group_data = {key: data[key] for key in ('group_name', 'description') if key in data}
        items = data.pop('data', None)  # This is the list of ProductGroupAttribute data
        success = False
        error = ''

        try:
            with db_client.session.begin():
                if product_group_data:
                    stmt = (
                        update(ProductGroup)
                        .where(ProductGroup.product_group_id == product_group_id)
                        .values(**product_group_data)
                    )
                    db_client.session.execute(stmt)

                compcode = request.args.get('current_user', {})
                cc = {
                    "compcode": compcode.get('company_id'),
                    "modified_on": datetime.datetime.now()
                }
                new_cc = {
                    "compcode": compcode.get('company_id'),
                    "created_on": datetime.datetime.now()
                }

                updateitemData = []
                itemdata = []
                provided_attributes_ids = set()
                for item in items:
                    if item.get('product_group_attribute_id'):
                        updateitemData.append({**item, **cc, 'deleted': False})
                        provided_attributes_ids.add(item['product_group_attribute_id'])
                    else:
                        itemdata.append({**item, **new_cc, "product_group_id": product_group_id, "deleted": False})

                existing_attributes = db_client.session.query(ProductGroupAttribute).filter_by(
                    product_group_id=product_group_id
                ).all()
                existing_attribute_ids = {attr.product_group_attribute_id for attr in existing_attributes}

                to_delete_ids = existing_attribute_ids - provided_attributes_ids


                if to_delete_ids:
                    db_client.session.query(ProductGroupAttribute).filter(
                        ProductGroupAttribute.product_group_attribute_id.in_(to_delete_ids)
                    ).update({"deleted": True}, synchronize_session=False)

                if updateitemData:
                    db_client.session.bulk_update_mappings(ProductGroupAttribute, updateitemData)
                if itemdata:
                    db_client.session.bulk_insert_mappings(ProductGroupAttribute, itemdata)

                success = True

        except SQLAlchemyError as e:
            error = f"Database error: {str(e)}"
            db_client.session.rollback()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': success,
            'message': "Update successful" if success else "Error in update",
            'error': error
        }


    @product_group_api_route.marshal_with(bulk_model_get)
    @login_required(permissions='product-group.view')
    def get(self, product_group_id):
        """
        Read user record / single record
        :param id:
        :return:
        """

        curr = request.args.get('current_user', {})
        compcode = curr.get('company_id', None)

        query = text('''
        select pg.product_group_id,pg.group_name,pg.description,pga.product_group_attribute_id,pga.attribute_id,pga.add_att,va.variant_attribute_name,pga.deleted from product_group as pg 
        left join product_group_attribute as pga on pg.product_group_id=pga.product_group_id
        left join variant_attribute as va on pga.attribute_id = va.variant_attribute_id where pg.deleted is not true and
        pga.deleted is not true and pg.compcode = :compcode and pg.product_group_id=:product_group_id
        ''')

        result = query_to_dict(db_client.engine.execute(query, compcode=compcode, product_group_id=product_group_id))

        return {
            'results':format(result)
        }

    @product_group_api_route.expect(bulk_model)
    @product_group_api_route.marshal_with(update_product_group_response)
    @login_required(permissions='product-group.edit')
    def put(self, product_group_id):
        """
        Update Employees record
        :return:
        """
        data = request.json
        response = self.put_record(data, product_group_id)
        return response

    @product_group_api_route.expect(bulk_model)
    @product_group_api_route.marshal_with(update_product_group_response)
    @login_required(permissions='product-group.edit')
    def patch(self, product_group_id):
        """
        Partial Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, product_group_id)
        return response

    @product_group_api_route.marshal_with(update_product_group_response)
    @login_required(permissions='product-group.delete')
    def delete(self, product_group_id):
        """
        Soft delete ProductGroup record
        TODO: Make soft delete
        :return:
        """
        result = update_local(
            model=ProductGroup,
            condition=ProductGroup.product_group_id == product_group_id,

            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result

######################################################################

    
    
