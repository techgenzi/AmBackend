import datetime
from flask import request, session
from flask_restx import Resource, abort
# from .. import ipss_db
from ipss_utils.ipss_api_doc import list_api_params, search_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, func, distinct, BigInteger, bindparam, Text, and_
from sqlalchemy.exc import SQLAlchemyError

from .errorhandling import map_sqlalchemy_error_to_http_status, update_local
from .helper import data_extract
from ..api_doc import search_filters
# from ..api_doc import pakage_collectionss_roles_fields
from ..models.pakages import PakageCollections, PakageItems
from ipss_utils.decorators import login_required

from ..routes.pakages import pakage_collections_api_route, pakage_collections_list_response, \
    create_pakage_collections_response, update_pakage_collections_model, update_pakage_collections_response, \
    create_bulk, pakage_collections_model
# from sqlalchemy import and_, text
from ..routes.pakages import create_pakage_collections_model, get_pakage_collections_response
from .. import ipss_db, db_client

# Primary p_key name

def querying():
    return text(r'''
       WITH cte AS (
        SELECT 
            ia.*, 
            jsonb_object_agg(ca.external_name, 
                CASE 
                    WHEN jsonb_typeof(attr.value) = 'array' THEN 
                        (attr.value->0->>'name')::text  -- Extract name and ensure it's text
                    ELSE 
                        TRIM(BOTH '\"' FROM attr.value::text)  -- Remove any extraneous quotes
                END) AS attributes
        FROM 
            ipss_assets ia
        JOIN LATERAL 
            jsonb_each(ia.asset_attributes::jsonb) AS attr(key, value) 
        ON 
            ia.asset_attributes IS NOT NULL 
            AND ia.asset_attributes::jsonb IS NOT NULL
        JOIN config_attributes ca ON ca.unique_id = attr.key
        WHERE 
            jsonb_typeof(ia.asset_attributes::jsonb) = 'object'  -- Ensure it's a JSON object
            and ia.deleted is not true --and ia.compcode=:c_code
        GROUP BY 
            ia.ipss_asset_id
        ORDER BY 
            ia.ipss_asset_id desc
    )
    ''')

primary_key = 'id'


@pakage_collections_api_route.route('/')
class PakageCollectionsApi(Resource):
    per_page = 20
    @pakage_collections_api_route.marshal_with(pakage_collections_list_response)
    @pakage_collections_api_route.doc(params={**list_api_params,**search_filters})
    # @user_verify(permission='Package_collection.list', db_client=db_client)
    @login_required(permissions='setitems.list')
    # @login_required()
    def get(self):
        """
        List of package_collections with pagination
        TODO: Search
        :return:
        """
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        sql_con=''
        if request.args.get('id'):
            sql_con+=' and pc.id=:id '
        if request.args.get('pakage_id'):
            sql_con+=' and pc.pakage_id=:pakage_id '
        if request.args.get('product_id'):
            sql_con+=' and pc.product_id=:product_id '
        if request.args.get('is_package_material'):
            sql_con+=' and pc.is_package_material=:is_package_material '
        sql_query=text(f'''
        with cte as (select distinct on (pc.pakage_id) pc.id,pc.pakage_id,pc.product_id,pc.needded_count,
        p.product_code,p.product_name as pakage_name,u.uom,
        p.sku_id pakage_sku 
        from package_collections pc 
        join products as p on p.product_id =pc.pakage_id 
        left join product_variant as pv on pv.product_id =pc.product_id 
        left join uom as u on u.id = p.uom_id
        where pc.deleted is not true and pc.compcode=:c_code {sql_con}
        limit :limit offset :offset 
        )
        select cte.*,
        json_agg(Distinct jsonb_build_object('product_code',p2.product_code,
        'product_name',p2.product_name,
        'pakage_id',pc.pakage_id,
        'product_id',pc.product_id,
        'is_package_material',pc.is_package_material,
        'product_sku',p2.sku_id,
        'uom_id',p2.uom_id,
        'uom', u2.uom,
        'id', pc.id,
        'needded_count',pc.needded_count)) as products
         from cte
        join package_collections pc on pc.pakage_id =cte.pakage_id 
        join products as p2 on p2.product_id =pc.product_id and pc.deleted is not true
        left join product_variant as pv2 on pv2.product_id =cte.product_id 
        left join uom as u2 on u2.id = p2.uom_id
 
        where 1=1 and pc.deleted is not true and pc.compcode=:c_code
        {sql_con}
        group by cte.id,cte.pakage_id,cte.product_id,cte.needded_count,cte.product_code,cte.pakage_name,cte.pakage_sku,cte.uom
        order by cte.id desc
        ''')
        sql_query=query_to_dict(db_client.engine.execute(sql_query,
                                                         id=request.args.get('id'),
                                                         is_package_material=request.args.get('is_package_material'),
                                                         product_id=request.args.get('product_id'),
                                                         pakage_id=request.args.get('pakage_id'),
                                                         limit=results_per_page,
                                                         c_code=ccode,
                                                         offset=offset
                                                         ))
        sql_count=text(f''' select count(distinct pakage_id) 
        from package_collections as pc
        where pc.deleted is not true and pc.compcode=:c_code 
        {sql_con}''')
        sql_count=query_to_dict(db_client.engine.execute(sql_count,
                                                         id=request.args.get('id'),
                                                         is_package_material=request.args.get('is_package_material'),
                                                         product_id=request.args.get('product_id'),
                                                         pakage_id=request.args.get('pakage_id'),
                                                         c_code=ccode,
                                                     ))
        return {
            "total_results": sql_count[0].get('count') if len(sql_count) else 0,
            "page": paged,
            "results_per_page": results_per_page,
            "results": sql_query}

    @login_required(permissions='setitems.add')
    # @user_verify(permission='Package_collection.add', db_client=db_client)
    @pakage_collections_api_route.expect(create_bulk)
    @pakage_collections_api_route.marshal_with(create_pakage_collections_response)
    def post(self):
        """
        Create package_collections record and return inserted id
        :return:
        """
        data = request.json
        # remove primary p_key if exists
        data=data.get('data')
        s = db_client.session
        compcode = request.args.get('current_user', {})
        cc = {"compcode": compcode.get('company_id'),
              "created_on": datetime.datetime.now()
              }
        data=[{**cc,**i} for i in data]
        package_id = None
        if data and data[0].get('pakage_id'):
            package_id = data[0].get('pakage_id')
        else:
            return {
                'success': False,
                'message': 'A value is required to post data'
            }, 400


        user = PakageCollections.query.filter(and_(PakageCollections.pakage_id == int(package_id), PakageCollections.deleted != True)).first()
        if user:
            return {
                'success': False,
                'message': 'Duplicate'
            }, 409
        try:
            print("SDfdsfsdfds")
            s.bulk_insert_mappings(mapper=PakageCollections, mappings=data)
            s.query(PakageItems).filter(PakageItems.pakage_id == package_id).delete(synchronize_session=False)
            s.commit()
            package_items=query_to_dict(db_client.engine.execute(data_extract(), pakage_id=package_id))
            if package_items:
                s.bulk_insert_mappings(mapper=PakageItems, mappings=package_items)
                s.commit()
        except SQLAlchemyError as e:
            s.flush()
            # s.rollback()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': True,
            'message': 'Recrod created succesfully'
        }

    @pakage_collections_api_route.expect(create_bulk)
    @pakage_collections_api_route.marshal_with(update_pakage_collections_response)
    # @user_verify(permission='Package_collection.edit', db_client=db_client)
    @login_required(permissions='setitems.edit')
    def put(self):
        """
        Update Employees record
        :return:
        """
        data=request.json
        data=data.get('data')
        compcode = request.args.get('current_user', {})
        cc = {"compcode": compcode.get('company_id'),
              "created_on": datetime.datetime.now(),
              }

        # print("dsfsd", package_items)
        post_data = [{**data.pop(i), **cc} for i in range(len(data) - 1, -1, -1) if not data[i].get('id')]
        package_id=data[0].get('pakage_id',None)
        error = ""
        try:
            if data:
                db_client.session.bulk_update_mappings(mapper=PakageCollections, mappings=data)
            if post_data:
                db_client.session.bulk_insert_mappings(mappings=post_data, mapper=PakageCollections)
            # if package_items:
            db_client.session.query(PakageItems).filter(PakageItems.pakage_id == package_id).delete(synchronize_session=False)
                # db_client.session.bulk_insert_mappings(mapper=PakageItems, mappings=package_items)
            collection_items=query_to_dict(db_client.engine.execute(data_extract(),pakage_id=package_id))
                                                                       # needded_count=data[0].get('needded_count'),
                                                                       # product_id=data[0].get('product_id')
                                                                       # )
            db_client.session.commit()
            if collection_items:
                db_client.session.bulk_insert_mappings(mappings=collection_items,mapper=PakageItems)
                db_client.session.commit()
            success=True
            c_code=200
        except Exception as e:
            db_client.session.rollback()
            return map_sqlalchemy_error_to_http_status(e)
        return {
            'success': success,
            'error': error,
        },c_code



@pakage_collections_api_route.route('/<id>/')
class EmployeeUpdateApi(Resource):
    @staticmethod
    def update_record(data, id):
        data.pop('id', None)

        result = update_local(
            model=PakageCollections,
            condition=PakageCollections.id == id,
            values=data
        )
        return result

    @pakage_collections_api_route.marshal_with(pakage_collections_model)
    # @user_verify(permission='RawMaterials.view', db_client=db_client)
    @login_required(permissions='setitems.view')
    def get(self, id):
        """
        Read user record / single record
        :param id:
        :return:
        """
        user = PakageCollections.query.filter_by(id=int(id)).first()
        return user



    @pakage_collections_api_route.expect(update_pakage_collections_model)
    @pakage_collections_api_route.marshal_with(update_pakage_collections_response)
    # @user_verify(permission='RawMaterials.edit', db_client=db_client)
    @login_required(permissions='setitems.edit')
    def patch(self, id):
        """
        Partial Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, id)
        return response

    @pakage_collections_api_route.marshal_with(update_pakage_collections_response)
    @login_required(permissions='setitems.delete')
    def delete(self, id):
        """
        Soft delete PakageCollections record
        TODO: Make soft delete
        :return:
        """
        result = update_local(
            model=PakageCollections,
            condition=PakageCollections.id == id,
            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result
@pakage_collections_api_route.route('/delete_pakage/<pakage_id>/')
class PakageDelete(Resource):
    @pakage_collections_api_route.marshal_with(update_pakage_collections_response)
    # @login_required(permissions='setitems.delete')
    def delete(self, pakage_id):
            """
            Soft delete PakageCollections record
            TODO: Make soft delete
            :return:
            """
            result = update_local(
                model=PakageCollections,
                condition=PakageCollections.pakage_id == pakage_id,
                values={
                    'deleted': True,
                    'deleted_at': datetime.datetime.now()
                }
            )
            return result

######################################################################

    
    
