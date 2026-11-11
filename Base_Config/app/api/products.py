import csv
import datetime
import json
import math
from collections import defaultdict
from io import StringIO, BytesIO
from pprint import pprint

from flask import request, session, Response
import pandas as pd
from flask_restx import Resource, abort, fields
# from .. import ipss_db
from ipss_utils.ipss_api_doc import list_api_params, search_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, func, distinct, BigInteger, insert, update, bindparam, NUMERIC, Integer, String
from sqlalchemy.exc import SQLAlchemyError

from .helper import get_product_sequence, seq, hash_check
from ..models.products import LocationProduct
from .errorhandling import map_sqlalchemy_error_to_http_status,update_local
# from ..api_doc import productss_roles_fields
from ..models.products import Products, ProductVariant, ProductsCostLog
from ipss_utils.decorators import login_required

from ..routes.products import products_api_route, products_list_response, create_products_response, \
    update_products_model, update_products_response, bulk_post_model, products_model, file_upload_parser, \
    products_drop_down_list_response
# from sqlalchemy import and_, text
from ..routes.products import create_products_model, get_products_response
from .. import ipss_db, db_client
from ..api_doc.product_api_doc import search_filters, form_fields
import hashlib

def generate_doc_id(tx_name,compcode):
    query = text('''
    select prefix,lastno,zeropadding from autogenerate 
    where compcode=:compcode and deleted is not true and tx_view_id =:tx_name
    ''')

    result = query_to_dict(db_client.engine.execute(query, compcode=compcode, tx_name=tx_name))
    seq = None
    if result:
        prefix = result[0].get('prefix', '')
        lastno = int(result[0].get('lastno', 0))
        zeropadding = int(result[0].get('zeropadding', 0))

        query_count = text('''
        select count(*) from products where compcode=:compcode 
        ''')
        count_result = query_to_dict(db_client.engine.execute(query_count,compcode=compcode))
        count = 0
        if count_result:
            count = count_result[0].get('count', 0)
            lastno += count
            seq = str(lastno).zfill(zeropadding)
            seq = f"{prefix}{seq}"
    return seq


# Primary p_key name

primary_key = 'product_id'


@products_api_route.route('/')
class productsApi(Resource):
    per_page = 20
    @products_api_route.marshal_with(products_list_response)
    @products_api_route.doc(params={**list_api_params, **search_filters})
    @login_required(permissions='product.list||bom.list||bom_config.list||Package_collection.list')
    def get(self):
        """
        List of Products with pagination
        TODO: Search
        :return:
        """
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        page = int(request.args.get('paged')) if request.args.get('paged') else 1
        result_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (page - 1) * result_per_page if (page - 1) * result_per_page else 0
        product_id = request.args.get('product_id', None)
        product_group_id = request.args.get('product_group_id', None)

        sql_con = ''
        if product_id:
            product_id = tuple(product_id.split(','))
            sql_con += ' and p.product_id in :product_id '
        if product_group_id:
            product_group_id = tuple(product_group_id.split(','))
            sql_con += ' and pg.product_group_id in :product_group_id '
        sql_query = text(f'''  
        SELECT 
    pg.product_group_id,
    pg.group_name,
    p.product_id,
    p.product_name,
    p.type,
    p.product_code,
    p.product_count,
    p.sku_id,
    p.description,
    p.base_uom,
    p.roql,
    p.cost,
    p.uom_id,
    p.allocated_quantity,
    u.uom,
    mc.cost as material_cost,
    b.bom_id,
    p.is_serializable,
    p.serialization_params,
    COALESCE(jsonb_agg(
        CASE 
            WHEN pv.product_variant_id IS NOT NULL THEN jsonb_build_object(
                'product_variant_id', pv.product_variant_id,
                'variant_attribute_id', va.variant_attribute_id,
                'variant_attribute_name', va.variant_attribute_name,
                'variant_value_id', vv.variant_value_id,
                'variant_value', vv.variant_value,
                'deleted', pv.deleted
            ) 
        END
    ) FILTER (WHERE pv.product_variant_id IS NOT NULL), '[]') AS data,
    COUNT(*) OVER() AS total_count
FROM product_group AS pg
LEFT JOIN products AS p ON pg.product_group_id = p.product_group_id
LEFT JOIN product_variant AS pv ON p.product_id = pv.product_id
LEFT JOIN variant_value AS vv ON pv.variant_value_id = vv.variant_value_id
LEFT JOIN variant_attribute AS va ON va.variant_attribute_id = vv.variant_attribute_id
LEFT JOIN uom AS u ON u.id = p.uom_id
left join bom b on b.product_id = p.product_id and b.deleted is not true
left join material_cost as mc on mc.product_id = p.product_id
WHERE pv.deleted IS NOT TRUE 
  AND p.deleted IS NOT TRUE 
  and u.deleted is not true
  and va.deleted is not true
  and vv.deleted is not true
  AND p.compcode = :compcode {sql_con}
GROUP BY 
    pg.product_group_id, pg.group_name, 
    p.product_id, p.product_name, 
    p.type, p.product_code, 
    p.product_count, p.sku_id, 
    p.description, p.base_uom, 
    p.roql, p.cost, p.uom_id, u.uom,
    p.allocated_quantity,
    mc.cost,b.bom_id,
    p.is_serializable,
    p.serialization_params
ORDER BY p.product_id DESC
LIMIT :limit OFFSET :offset;
               ''')
        sql_query = query_to_dict(db_client.engine.execute(sql_query,
                                                           limit=result_per_page,
                                                           offset=offset,
                                                           compcode=ccode,
                                                           product_id=product_id,
                                                           product_group_id=product_group_id))
        # result = format(sql_query)
        return {
            "total_results": sql_query[0].get('total_count', 0) if sql_query else 0,
            "page": page,
            "results_per_page": result_per_page,
            "results": sql_query
        }

    @login_required(permissions='product.add')
    @products_api_route.expect(bulk_post_model)
    @products_api_route.marshal_with(create_products_response)
    def post(self):
        """
        Create Products record and return inserted id
        :return:
        """
        data = request.json
        items = data.pop('data', None)
        data.pop('product_id', None)
        product_name = data.get('product_name', None)
        product_group_id = data.get('product_group_id', None)
        s = db_client.session
        data['sku_id'] = get_product_sequence(s)
        # print("Code Generated")
        compcode = request.args.get('current_user', {})
        cc = {"compcode": compcode.get('company_id'),
              "created_on": datetime.datetime.now(),
              "created_by": compcode.get('username')
              }
        variant_value_ids = []
        itemdata = []
        for i in items:
            itemdata.append({**i, **cc})
            variant_value_ids.append(i.get('variant_value_id', None))

        variant_value_ids = tuple(variant_value_ids) or (None,)
        seq_query = text('''
            select vv.variant_attribute_id as attribute_id,vv.variant_value as value from variant_value as vv 
            where variant_value_id in :variant_value_ids
        ''')
        value = query_to_dict(db_client.engine.execute(seq_query, variant_value_ids=variant_value_ids))
        data['product_code'] = seq(product_group_id,value,product_name)
        hash_value = hash_check(product_group_id=product_group_id, product_name=product_name, compcode=compcode.get('company_id'), variant_value_ids=variant_value_ids, product_id=None)
        data['hash_value'] = hash_value
        try:
            stmt = (
                insert(Products).values(**data, **cc).returning(Products.product_id)
            )
            result = s.execute(stmt)
            primary_key_id = result.scalar()
            if primary_key_id:
                if itemdata:
                    itemdata = [{**i, **{"product_id": primary_key_id}} for i in itemdata]
                    s.bulk_insert_mappings(mapper=ProductVariant, mappings=itemdata)
            s.commit()
        except SQLAlchemyError as e:
            s.flush()
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': True,
            'message': "Records created Successfully"
        }


@products_api_route.route('/<product_id>/')
class EmployeeUpdateApi(Resource):
    @staticmethod
    def update_record(data, product_id):
        # data.pop('product_id', None)
        # return result
        data.pop('product_id', None)
        items = data.pop('data', None)
        success = False
        error = ''
        try:
            with db_client.session.begin():
                stmt = (
                    update(Products)
                    .where(Products.product_id == product_id)
                    .values(**data)
                )
                db_client.session.execute(stmt)
                compcode = request.args.get('current_user', {})
                cc = {"compcode": compcode.get('company_id'),
                      "modified_on": datetime.datetime.now()
                      }
                updateitemData = [{**items.pop(i), **cc} for i in range(len(items) - 1, -1, -1) if
                                  items[i].get('product_variant_id')]
                itemdata = [{**i, **{"product_id": product_id}, **cc} for i in items]
                if updateitemData:
                    for i in updateitemData:
                        if i.get('deleted', '').lower() == 'true':
                            i['deleted'] = True
                if updateitemData:
                    db_client.session.bulk_update_mappings(mapper=ProductVariant, mappings=updateitemData)
                if itemdata:
                    db_client.session.bulk_insert_mappings(mapper=ProductVariant, mappings=itemdata)
                success = True
        except SQLAlchemyError as e:
            error = str(e)
            db_client.session.flush()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': success,
            'message': "update successfully" if success else "error in updation",
            'error': error
        }

    @staticmethod
    def put_record(data, product_id):
        data.pop('product_id', None)
        product_data = {key: data[key] for key in ('product_name', 'description','cost', 'roql', 'uom_id', 'is_serializable', 'serialization_params') if key in data}
        items = data.pop('data', None)
        success = False
        error = ''

        try:
            with db_client.session.begin():
                variant_value_ids = []
                compcode = request.args.get('current_user', {})
                cc = {
                    "compcode": compcode.get('company_id'),
                    "modified_on": datetime.datetime.now()
                }
                new_cc = {
                    "compcode": compcode.get('company_id'),
                    "created_on": datetime.datetime.now()
                }
                provided_attribute_ids = {
                    item['product_variant_id']
                    for item in items if item.get('product_variant_id')
                }

                existing_attributes = db_client.session.query(ProductVariant).filter(
                    ProductVariant.product_id == product_id,
                    ProductVariant.deleted != True
                ).all()
                response = db_client.session.query(Products).filter_by(
                    product_id=product_id
                ).first()
                product_group_id = response.product_group_id

                existing_attribute_ids = {attr.product_variant_id for attr in existing_attributes}

                existing_variant_value_id = {attr.variant_value_id for attr in existing_attributes}

                to_delete_ids = existing_attribute_ids - provided_attribute_ids
                ##
                # itemdata = []

                ##
                print(to_delete_ids)
                updateitemData = []
                itemdata = []
                current_variant_value_ids = set()

                for item in items:

                    if item.get('product_variant_id'):
                        updateitemData.append({**item, **cc, 'deleted': False})
                    else:
                        itemdata.append({**item, **new_cc, "product_id": product_id, "deleted": False})
                    if item.get('variant_value_id'):
                        current_variant_value_ids.add(item.get('variant_value_id'))
                        variant_value_ids.append(item.get('variant_value_id', None))

                variant_value_ids = tuple(variant_value_ids) or (None,)
                seq_query = text('''
                                    select vv.variant_attribute_id as attribute_id,vv.variant_value as value from variant_value as vv 
                                    where variant_value_id in :variant_value_ids
                                ''')
                value = query_to_dict(db_client.engine.execute(seq_query, variant_value_ids=variant_value_ids))
                hash_value = hash_check(product_group_id=product_group_id, product_name=product_data.get('product_name', None),
                           variant_value_ids=tuple(current_variant_value_ids), compcode=compcode.get('company_id'),
                           product_id=product_id)
                product_data['hash_value'] = hash_value
                product_name = ''
                if product_data.get('product_name'):
                    product_name = product_data.get('product_name')
                else:
                    query_temp = text(''' select product_name from products where product_id=:product_id''')
                    product_name = query_to_dict(db_client.engine.execute(query_temp,product_id=product_id))[0].get('product_name')
                product_data['product_code'] = seq(product_group_id=product_group_id, productname=product_name, value = value)
                cost_log = {}
                if product_data.get('cost'):
                    product_data['effective_date'] = datetime.datetime.now()
                    cost_log['effective_date'] = datetime.datetime.now()
                    cost_log['product_id'] = product_id
                    cost_log['cost'] = product_data.get('cost')
                    cost_log['modified_by'] = compcode.get('username')
                if product_data:
                    stmt = (
                        update(Products)
                        .where(Products.product_id == product_id)
                        .values(**product_data)
                    )
                    db_client.session.execute(stmt)
                if cost_log:
                    stmt2 = (
                        insert(ProductsCostLog).values(**cost_log)
                    )
                    db_client.session.execute(stmt2)

                if to_delete_ids:
                    db_client.session.query(ProductVariant).filter(
                        ProductVariant.product_variant_id.in_(to_delete_ids)
                    ).update({"deleted": True}, synchronize_session=False)

                if updateitemData:
                    db_client.session.bulk_update_mappings(mapper=ProductVariant, mappings=updateitemData)
                if itemdata:
                    db_client.session.bulk_insert_mappings(mapper=ProductVariant, mappings=itemdata)

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

    @products_api_route.marshal_with(products_model)
    @login_required(permissions='product.view')
    def get(self, product_id):
        """
        Read user record / single record
        :param id:
        :return:
        """
        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id')

        sql_query = text(f'''  
        SELECT 
            pg.product_group_id,
            pg.group_name,
            p.product_id,
            p.product_name,
            p.type,
            p.product_code,
            p.product_count,
            p.sku_id,
            p.description,
            p.base_uom,
            p.roql,
            p.cost,
            p.uom_id,
            p.allocated_quantity,
            u.uom,
            mc.cost as material_cost,
            b.bom_id,
            p.is_serializable,
            p.serialization_params,
            COALESCE(jsonb_agg(
                CASE 
                    WHEN pv.product_variant_id IS NOT NULL THEN jsonb_build_object(
                        'product_variant_id', pv.product_variant_id,
                        'variant_attribute_id', va.variant_attribute_id,
                        'variant_attribute_name', va.variant_attribute_name,
                        'variant_value_id', vv.variant_value_id,
                        'variant_value', vv.variant_value,
                        'deleted', pv.deleted
                    ) 
                END
            ) FILTER (WHERE pv.product_variant_id IS NOT NULL), '[]') AS data
        FROM product_group AS pg
        LEFT JOIN products AS p ON pg.product_group_id = p.product_group_id
        LEFT JOIN product_variant AS pv ON p.product_id = pv.product_id AND pv.deleted IS NOT TRUE
        LEFT JOIN variant_value AS vv ON pv.variant_value_id = vv.variant_value_id AND vv.deleted IS NOT TRUE
        LEFT JOIN variant_attribute AS va ON va.variant_attribute_id = vv.variant_attribute_id AND va.deleted IS NOT TRUE
        LEFT JOIN uom AS u ON u.id = p.uom_id AND u.deleted IS NOT TRUE
        LEFT JOIN bom AS b ON b.product_id = p.product_id AND b.deleted IS NOT TRUE
        LEFT JOIN material_cost AS mc ON mc.product_id = p.product_id
        WHERE p.deleted IS NOT TRUE 
          AND p.compcode = :compcode 
          AND p.product_id = :product_id
        GROUP BY 
            pg.product_group_id, pg.group_name, 
            p.product_id, p.product_name, 
            p.type, p.product_code, 
            p.product_count, p.sku_id, 
            p.description, p.base_uom, 
            p.roql, p.cost, p.uom_id, u.uom,
            p.allocated_quantity,
            mc.cost, b.bom_id,
            p.is_serializable, p.serialization_params
        ORDER BY p.product_id DESC
                       ''')
        sql_query = query_to_dict(db_client.engine.execute(sql_query,
                                                           compcode=compcode,
                                                           product_id=product_id))
        return sql_query[0] if sql_query else None

    @products_api_route.expect(update_products_model)
    @products_api_route.marshal_with(update_products_response)
    @login_required(permissions='product.edit')
    def put(self, product_id):
        """
        Update Employees record
        :return:
        """
        data = request.json
        response = self.put_record(data, product_id)
        return response

    @products_api_route.expect(products_model)
    @products_api_route.marshal_with(update_products_response)
    @login_required(permissions='product.edit')
    def patch(self, product_id):
        """
        Partial Update Employees record
        :return:
        """
        data = request.json
        data.pop('group_name', None)
        data.pop('product_id', None)
        response = self.update_record(data, product_id)
        return response

    @products_api_route.marshal_with(update_products_response)
    @login_required(permissions='product.delete')
    def delete(self, product_id):
        """
        Soft delete Products record
        TODO: Make soft delete
        :return:
        """

        result = update_local(
            model=Products,
            condition=Products.product_id == product_id,
            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result

######################################################################
stock_manage_model=products_api_route.model('stock_manage_model',{"product_count":fields.String,
                                                                  "product_id":fields.Integer,
                                                                  'store_id': fields.Integer,
                                                                  'ref_id': fields.String,
                                                                  'serial_numbers': fields.List(fields.String)})
stock_manage_response=products_api_route.model('stock_manage_response',{
    "data":fields.List(fields.Nested(stock_manage_model))
})
@products_api_route.route('/stock-managing')
class Stock(Resource):
    @products_api_route.expect(stock_manage_response)
    @products_api_route.marshal_with(update_products_response)
    @login_required()
    def put(self):
        data = request.json
        data = data.get('data')
        curr = request.args.get('current_user',{})
        compcode = curr.get('company_id')
        sql_query=text('''
        update products set product_count= COALESCE(product_count,0)::numeric + cast(:product_count as numeric)
        where product_id=:product_id
        ''').bindparams(
            product_count=bindparam('product_count', type_=NUMERIC),
        product_id=bindparam('product_id', type_=Integer)
        )
        store_check_query = text('''      
            select 
            case 
            when 
                exists(
                    select 1 from store_product as sp where sp.deleted is not true 
                    and sp.product_id =:product_id 
                    and sp.store_id =:store_id 
                    and COALESCE(sp.lot_no, '') = COALESCE(:lot_no, '')
                    and sp.compcode =:compcode )
            then 0
            else 1
            end
        ''').bindparams(
            store_id=bindparam('store_id', type_=Integer),
            product_id=bindparam('product_id', type_=Integer),
            compcode=bindparam('compcode', type_=Integer),
            lot_no=bindparam('lot_no', type_=String)
        )
        update_query = text('''
        update store_product set product_count= COALESCE(product_count,0)::numeric + cast(:product_count as numeric)
        where product_id=:product_id and store_id=:store_id and COALESCE(lot_no, '') = COALESCE(:lot_no, '') and compcode=:compcode and deleted is not true
        ''').bindparams(
        product_count=bindparam('product_count', type_=NUMERIC),
        product_id=bindparam('product_id', type_=Integer),
        store_id = bindparam('store_id', type_=Integer),
        compcode= bindparam('compcode', type_=Integer),
        lot_no=bindparam('lot_no', type_=String)
        )
        insert_invregistry = text('''
        INSERT INTO invregistry (
            product_id, requested_amount, approved_amount, action, ref_id, 
            status, is_dispatch, store_id, compcode, userid, approval_id, 
            approval_date, created_on, created_by, type, deleted, lot_no
        ) VALUES (
            :product_id, :product_count, :product_count, 'Inward', :ref_id, 
            'Approved', false, :store_id, :compcode, :userid, :userid, 
            NOW(), NOW(), :username, 'GRN', false, :lot_no
        )
        ''').bindparams(
            product_id=bindparam('product_id', type_=Integer),
            product_count=bindparam('product_count', type_=NUMERIC),
            ref_id=bindparam('ref_id', type_=String),
            store_id=bindparam('store_id', type_=Integer),
            compcode=bindparam('compcode', type_=Integer),
            userid=bindparam('userid', type_=Integer),
            username=bindparam('username', type_=String),
            lot_no=bindparam('lot_no', type_=String)
        )
        cc = {
            'compcode': compcode,
            'created_by': curr.get('username'),
            'created_on': datetime.datetime.now()
        }
        s = db_client.session
        try:
            for row in data:
                row_copy = dict(row)
                serials = row_copy.pop('serial_numbers', None)
                ref_id = row_copy.pop('ref_id', 'GRN-Inward')
                s.execute(sql_query, row_copy)
                
                # Insert inward movement record into invregistry
                s.execute(insert_invregistry, {
                    'product_id': row_copy.get('product_id'),
                    'product_count': row_copy.get('product_count'),
                    'ref_id': ref_id,
                    'store_id': row_copy.get('store_id'),
                    'compcode': compcode,
                    'userid': curr.get('userid'),
                    'username': curr.get('username'),
                    'lot_no': row_copy.get('lot_no') or None
                })

                if 'store_id' in row_copy:
                    params = {
                        'store_id': row_copy.get('store_id'),
                        'product_id': row_copy.get('product_id'),
                        'product_count': row_copy.get('product_count'),
                        'lot_no': row_copy.get('lot_no'),
                        'compcode': compcode
                    }
                    result = s.execute(store_check_query, params).fetchone()
                    print(result)
                    if result and result[0]==1:
                        loc_product_data = {
                            'store_id': row_copy.get('store_id'),
                            'product_id': row_copy.get('product_id'),
                            'product_count': row_copy.get('product_count'),
                            'lot_no': row_copy.get('lot_no'),
                            **cc
                        }
                        stmt = insert(LocationProduct).values(**loc_product_data)
                        s.execute(stmt)
                    else:
                        s.execute(update_query, params)
                    
                    if serials:
                        import json
                        for unit in serials:
                            if isinstance(unit, str):
                                serial_val = unit.strip()
                                unit_data_json = None
                            elif isinstance(unit, dict):
                                serial_key = next((k for k in unit.keys() if k.lower() in ('serial_number', 'serial no', 'serial number', 'serial_no')), None)
                                serial_val = str(unit[serial_key]).strip() if serial_key else str(list(unit.values())[0]).strip()
                                unit_data_json = json.dumps(unit)
                            else:
                                continue
                            
                            if serial_val:
                                s.execute(text('''
                                    insert into public.store_serialized_products (product_id, store_id, serial_number, unit_data, compcode)
                                    values (:product_id, :store_id, :serial_number, :unit_data, :compcode)
                                    on conflict (compcode, product_id, serial_number) do update 
                                    set store_id = excluded.store_id, unit_data = excluded.unit_data, status = 'Available', deleted = false
                                '''), {
                                    'product_id': row_copy['product_id'],
                                    'store_id': row_copy['store_id'],
                                    'serial_number': serial_val,
                                    'unit_data': unit_data_json,
                                    'compcode': compcode
                                })
            s.commit()
        except Exception as e:
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': True
        }



@products_api_route.route('/update-cost')
class Cost(Resource):

    @login_required()
    @products_api_route.doc(params = {
        'product_group_id':{
            'type':int,
            'description': 'filter by product group id'
        }
    })
    def get(self):
        product_group_id = request.args.get('product_group_id', None)
        s = db_client.session
        data = s.query(
            Products.sku_id,
            Products.product_code,
            Products.cost
        ).filter(
            Products.deleted.isnot(True)
        )

        if product_group_id:
            data = data.filter(Products.product_group_id == product_group_id)
        data = data.all()

        si = StringIO()
        csv_writer = csv.writer(si)

        headers = ['sku_id', 'product_name', 'cost']
        csv_writer.writerow(headers)

        for row in data:
            csv_writer.writerow(row)

        df = pd.DataFrame(data, columns=headers)
        # print(df, "RTY")
        # return

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')

        output.seek(0)

        response = Response(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment;filename=products.xlsx"}
        )
        return response

    @login_required()
    @products_api_route.doc(params=form_fields)
    def post(self):

        s = db_client.session
        username = request.args.get('current_user', {}).get('username')
        file = request.files['File']

        if not file:
            return {'error': 'No file uploaded'}, 400

        try:
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file)
            elif file.filename.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file)
            else:
                return {'error': 'Unsupported file format'}, 400

            if not {'Product Code', 'Cost per UOM'}.issubset(df.columns):
                return {'error': 'File must contain sku_id and cost columns'}, 400

            update_data = df.to_dict(orient='records')
            cost_insert = []
            for i in update_data:
                sku_id = i.pop('Product Code')
                i['effective_date'] = datetime.datetime.now()
                if i.get('Cost per UOM') is None or (isinstance(i['Cost per UOM'], float) and math.isnan(i['Cost per UOM'])):
                    i['Cost per UOM'] = 0
                cost = i.pop('Cost per UOM')
                print(i)
                update_local(model=Products, condition=Products.sku_id == sku_id, values={'cost': cost}, s=s, commit=False)
                product_id = s.query(
                    Products.product_id
                ).filter(Products.sku_id == sku_id).scalar()
                i.pop('product_code', None)
                i.pop('modified_on', None)
                i['modified_by'] = username
                cost_insert.append({'product_id': product_id, **i})

            s.bulk_insert_mappings(mapper=ProductsCostLog, mappings=cost_insert)

            s.commit()

            return {'message': 'Bulk update completed successfully'}, 200

        except Exception as e:
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)


@products_api_route.route('/product-dropdown')
class ProductDropDown(Resource) :

    @products_api_route.marshal_with(products_drop_down_list_response)
    @products_api_route.doc(params={**list_api_params, **search_filters})
    @login_required(permissions='product.list||bom.list||bom_config.list||Package_collection.list')
    def get(self):
        """
        List of Products For Drop Down
        TODO: Search
        :return:
        """
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        product_id = request.args.get('product_id', None)
        product_group_id = request.args.get('product_group_id', None)

        sql_con = ''
        if product_id:
            product_id = tuple(product_id.split(','))
            sql_con += ' and p.product_id in :product_id '
        if product_group_id:
            product_group_id = tuple(product_group_id.split(','))
            sql_con += ' and pg.product_group_id in :product_group_id '
        sql_query = text(f''' 
SELECT 
        p.product_id,
        p.product_group_id,
        pg.group_name,
        p.product_name,
        p.product_code,
        p.sku_id,
        p.uom_id,
        u.uom,
        b.bom_id,
        COUNT(*) OVER() AS total_count
    FROM product_group AS pg
    LEFT JOIN products AS p ON pg.product_group_id = p.product_group_id
    LEFT JOIN uom AS u ON u.id = p.uom_id
    left join bom b on b.product_id = p.product_id and b.deleted is not true
    WHERE p.deleted IS NOT TRUE 
      and u.deleted is not true AND p.compcode = :compcode {sql_con}
    ORDER BY p.product_id DESC
                   ''')
        sql_query = query_to_dict(db_client.engine.execute(sql_query,
                                                           # limit=result_per_page,
                                                           # offset=offset,
                                                           compcode=ccode,
                                                           product_id=product_id,
                                                           product_group_id=product_group_id))
        # result = format(sql_query)
        return {
            "total_results": sql_query[0].get('total_count', 0) if sql_query else 0,
            "results": sql_query
        }

    
