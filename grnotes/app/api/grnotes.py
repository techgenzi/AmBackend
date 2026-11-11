import datetime
from audioop import error

from flask import request
from flask_restx import Resource, marshal
from ipss_utils.decorators import login_required
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, update
from sqlalchemy.exc import SQLAlchemyError
from .errorhandling import map_sqlalchemy_error_to_http_status
# from joborder.app.api_doc import items
from .. import ipss_db, db_client
from ipss_utils.ipss_api_doc import list_api_params
from .helper import update_purchase_order, delete_func
from ..api_doc import grnotes_list_request, search_params
from ..models.grnotes import GRNotes, GRNLineItems

from ..routes.grnotes import grnotes_api_route, grnotes_list_response, create_grnotes_response, \
    update_grnotes_model, update_grnotes_response, grnotes_get_response, grnotes_bulk_list_response, items_model, grnline_model, grnotes_fields
from ..routes.grnotes import create_grnotes_model, get_grnotes_response

# Primary key name
primary_key = 'grnotesid'

def sequence(prefix,lastno,zeropadding,compcode,table):
    if not lastno:
        lastno = 0
    if not zeropadding:
        zeropadding = 6
    else:
        zeropadding = int(zeropadding)

    query = text(f''' select count(*) from {table} where compcode=:compcode ''')
    res = query_to_dict(db_client.engine.execute(query, compcode=compcode))
    count = 0
    if res:
        count = res[0].get('count')
    next_no = int(lastno)+count+1
    formatnum = str(int(next_no)).zfill(zeropadding)
    sequenc_num = f"{prefix}{formatnum}"
    return sequenc_num



@grnotes_api_route.route('/')
class GRN(Resource):
    per_page = 20

    @grnotes_api_route.marshal_with(grnotes_get_response)
    @grnotes_api_route.doc(params=grnotes_list_request)
    @login_required(permissions='GoodsNote.list||Returns.list||InventoryReturns.list')
    def get(self):
        """
        List of Grnotes with pagination
        TODO: Search Grnote
        :return:
        """
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else self.per_page
        offset = (paged - 1) * results_per_page
        # print(offset)
        sql_query_count = text("SELECT COUNT(grnotes.grnotesid) as total "
                               "FROM grnotes  WHERE grnotes.deleted = 'false' ")

        grnotesid = request.args.get('grnotesid')
        type = request.args.get('types')
        current_user = request.args.get('current_user')
        # print("current_user",current_user)
        ccode = current_user.get('company_id')
        # Condition based sql query
        if type is not None:
            types = "grnotes.type = :type AND "
        else:
            types = "grnotes.type !='purchase_order' AND "
        sql_condition = ""
        if grnotesid and grnotesid != "ALL":
            sql_condition += "grnotes.grnotesid = :grnotesid AND "
        # if types and types != "ALL":
        #     sql_condition += "grnotes.type = :types AND "
        query = text(" SELECT "
                     "grnotes.deliverychallan_no,"
                     "grnotes.invice_attach,"
                     "grnotes.dc_attach,"
                     "grnotes.grnotesid as grnotesid,"
                     "grnotes.user_id as user_id,"
                     "grnotes.deliverychallan_no,"
                     "grnotes.vendorid,"
                     "v.companyname,"
                     "v.contactname,"
                     "v.emailid,"
                     "v.mobileno,"
                     "jo.joborderid as joborderid,"
                     "jo.joborderproposalid as joborderproposalid,"
                     "jo.joborderno as joborderno,"
                     "jo.jo_status as jo_status,"
                     "jo.jo_doc as jo_doc,"
                     "jo.jo_valid_date as jo_valid_date,"
                     "jo.purchase_orderno as purchase_orderno,"
                     "jo.jo_date as jo_date,"
                    "COALESCE(grnotes.vendorid, jo.vendorid) AS vendorid,"
                    "COALESCE(v.companyname, jo.companyname) AS companyname,"
                    "COALESCE(v.contactname, jo.contactname) AS contactname,"
                    "COALESCE(v.emailid, jo.emailid) AS emailid,"
                    "COALESCE(v.mobileno, jo.mobileno) AS mobileno,"
                     "jo.jo_aql as jo_aql,"
                     "grnotes.bommaster_id as bommaster_id,"
                     "(SELECT bom_master.bom_no as bom_no from bom_master where bom_master.bommaster_id=grnotes.bommaster_id ), "
                     ""
                     "jo.termsand_condition as jo_termsand_condition,"
                     "grnotes.inviceno as inviceno,"
                     "grnotes.grn_no as grn_no,"
                     "grnotes.is_moved,"
                     "grnotes.total_item,"
                     "grnotes.total_price,"
                     "grnotes.grndate as grndate,"
                     "grnotes.invice_attach as invice_attach, "
                     "grnotes.deliverychallan_no as deliverychallan_no,"
                     "grnotes.dc_attach as dc_attach,"
                     "grnotes.grn_reason as grn_reason,"
                     "grnotes.grn_description as grn_description,"
                     "grnotes.type as type,"
                     "grnotes.created_on as created_on,"
                     "grnotes.created_by as created_by,"
                     "grnotes.modified_on as modified_on,"
                     "grnotes.modified_by as modified_by,"
                     "grnotes.deleted as deleted,"
                     "grnotes.deleted_at as deleted_at,"
                     "grnotes.compcode as compcode, "
                     "grnotes.is_qc_done as is_qc_done, "
                     "(SELECT sl.store_name FROM invregistry ir JOIN store_location sl ON ir.store_id = sl.store_id WHERE ir.ref_id = grnotes.grn_no AND ir.compcode = grnotes.compcode AND ir.deleted IS NOT TRUE ORDER BY ir.releseid DESC LIMIT 1) as store_name, "
                     "(SELECT ir.store_id FROM invregistry ir WHERE ir.ref_id = grnotes.grn_no AND ir.compcode = grnotes.compcode AND ir.deleted IS NOT TRUE ORDER BY ir.releseid DESC LIMIT 1) as store_id "
                     "FROM grnotes "
                     "LEFT JOIN joborder as jo ON grnotes.joborderid = CAST(jo.joborderid as VARCHAR) "
                     "LEFT JOIN vendor as v ON grnotes.vendorid = v.vendorid "
                     f"WHERE grnotes.compcode = :compcode AND grnotes.deleted = 'false' AND {sql_condition} {types} 1=1 "
                     "ORDER BY grnotes.created_on DESC "
                     "LIMIT :limit OFFSET :offset"
                     )
        sql_count=text(f'''select count(distinct grnotesid) 
                     FROM grnotes 
                     LEFT JOIN joborder as jo ON grnotes.joborderid = CAST(jo.joborderid as VARCHAR) 
                     LEFT JOIN vendor as v ON grnotes.vendorid = v.vendorid 
                     WHERE grnotes.compcode = :compcode AND grnotes.deleted = 'false' AND {sql_condition} {types} 1=1 ''')
        sql_count=query_to_dict(db_client.engine.execute(
            sql_count,
            compcode=ccode,
            grnotesid=grnotesid,
            type=type))
        results = query_to_dict(db_client.engine.execute(
            query,
            compcode=ccode,
            grnotesid=grnotesid,
            type=type,
            limit=results_per_page,
            offset=offset
        ))
        count_result = query_to_dict(db_client.engine.execute(sql_query_count))
        print(("asd", count_result))
        print(results)
        return {

            'primary_key': primary_key,
            'total_results':sql_count[0].get('count') if len(sql_count) else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': results
        }

    @login_required(permissions='GoodsNote.add||Returns.add||InventoryReturns.add')
    @grnotes_api_route.expect(items_model)
    @grnotes_api_route.marshal_with(create_grnotes_response)
    def post(self):
        """
        Create GRNotes record and return inserted id
        :return:
        """
        data=request.json
        items=data.pop('items', None)
        cur = request.args.get('current_user', {})
        ccode = cur.get('company_id', None)
        query = text('''
        SELECT COALESCE(MAX(NULLIF(regexp_replace(grn_no, '\\D', '', 'g'), '')::integer), 0) AS max_no
        FROM grnotes 
        WHERE compcode = :compcode
        ''')
        result = query_to_dict(db_client.engine.execute(query, compcode=ccode))
        max_no = result[0].get('max_no', 0) if len(result) else 0
        next_no = int(max_no) + 1
        formatnum = str(int(next_no)).zfill(6)
        sequenc_num = f"GRN-{formatnum}"
        print(sequenc_num)
        data['grn_no'] = sequenc_num
        error=''
        s = db_client.session
        try:
            # Perform the bulk update
            with s.begin():
                result = ipss_db.insert_record(
                    model=GRNotes,
                    values=data,
                    commit=False
                )
                if not result.get('success'):
                    return result, 409
                compcode = request.args.get('current_user', {})

                cc = {"compcode": compcode.get('company_id'),
                      "created_on": datetime.datetime.now(),
                      'grnotesid': result.get('primary_key_id')[0]
                      }

                post_item = []
                update_item = []
                for i in items:
                    post_item.append({**i, **cc})
                    if i.get('purchase_items_id') is not None:
                        update_item.append(i)

                s.bulk_insert_mappings(mapper=GRNLineItems, mappings=post_item)
                if update_item:
                    s.execute(update_purchase_order(), update_item)

        except Exception as e:
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': True,
            'message': 'Records created successfully'
        }





@grnotes_api_route.route('/<GRNotes_id>/')
class UsersUpdateApi(Resource):
    @staticmethod
    def update_record(data, GRNotes_id):
        data.pop(primary_key, None)
        result = ipss_db.update_record(
            model=GRNotes,
            condition=GRNotes.grnotesid == GRNotes_id,
            values=data
        )
        return result


    @grnotes_api_route.marshal_with(items_model)
    @login_required(permissions='GoodsNote.view||Returns.view||InventoryReturns.view||GoodsNote.edit')
    def get(self, GRNotes_id):
        """
        Read GRNotes record / single record
        :param GRNotes:
        :return:
        """
        ccode = request.args.get('current_user').get('company_id')
        # print(request.args.get('current_user').get('username'))
        user = GRNotes.query.filter_by(grnotesid=GRNotes_id).first()
        # line = GRNLineItems.query.filter_by(grnotesid=GRNotes_id).all()

        query = text('''
        select gln.*,p.product_name,p.product_code,jli.quandity,jli.quantity_delivered,uom.uom,p.uom_id,
               jli.lot_no, jli.product_details
        from grnlineitems as gln 
        left join products as p on gln.product_id = p.product_id
        left join uom on uom.id =uom_id 
		left join joline_items as jli on gln.purchase_items_id = jli.id
        where gln.deleted is not true and gln.grnotesid=:grnotesid
        ''')
        items = query_to_dict(db_client.engine.execute(query,grnotesid=GRNotes_id,ccode=ccode))
        print(items)
        user_data = marshal(user, grnotes_fields)
        store_q = text(
            """SELECT ir.store_id, sl.store_name 
            FROM invregistry ir 
            JOIN store_location sl ON ir.store_id = sl.store_id 
            WHERE ir.ref_id = :ref_id AND ir.compcode = :compcode AND ir.deleted IS NOT TRUE 
            ORDER BY ir.releseid DESC LIMIT 1"""
        )
        store_row = db_client.engine.execute(store_q, ref_id=user.grn_no, compcode=ccode).first() if user and user.grn_no else None
        if store_row:
            user_data['store_id'] = store_row[0]
            user_data['store_name'] = store_row[1]
        else:
            user_data['store_id'] = None
            user_data['store_name'] = None
        user_data['items'] = items
        return user_data

    @grnotes_api_route.expect(items_model)
    @grnotes_api_route.marshal_with(update_grnotes_response)
    @login_required(permissions='GoodsNote.edit||Returns.edit||InventoryReturns.edit')
    def put(self, GRNotes_id):

        """
        Update GRNLINE Items bulk patch
        :return:
        """

        data = request.json

        items = data.pop('items', None)
        data.pop('grnotes_id', None)
        s = db_client.session
        try:
            # Perform the bulk update
            with s.begin():
                que = (update(GRNotes).where(GRNotes.grnotesid==GRNotes_id).values(data))
                db_client.engine.execute(que)

                if items:
                    update_data = []
                    post_data = []
                    for item in items:
                        if 'grnlineid' in item:
                            update_data.append(item)
                        else:
                            item['grnotesid'] = GRNotes_id
                            item['compcode'] = request.args.get('current_user', {}).get('company_id')
                            item['created_on'] = datetime.datetime.now()
                            item['created_by'] = request.args.get('current_user', {}).get('username')
                            post_data.append(item)
                    if update_data:
                        s.bulk_update_mappings(GRNLineItems, update_data)
                    if post_data:
                        s.bulk_insert_mappings(GRNLineItems, post_data)

        except Exception as e:
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': True,
            'message': 'Bulk update successful'}, 200

    @grnotes_api_route.expect(update_grnotes_model)
    @grnotes_api_route.marshal_with(update_grnotes_response)
    @login_required(permissions='GoodsNote.edit||Returns.edit||InventoryReturns.edit')
    def patch(self, GRNotes_id):
        """
        Partial Update GRNotes record
        :return:
        """
        data = request.json
        response = self.update_record(data, GRNotes_id)
        print("vendor", response)
        return response

    @grnotes_api_route.marshal_with(update_grnotes_response)
    @login_required(permissions='GoodsNote.delete||Returns.delete||InventoryReturns.delete')
    def delete(self, GRNotes_id):
        """
        Soft delete / reverse GRNotes record
        """
        current_user = request.args.get('current_user', {})
        reason = request.args.get('reason')
        if not reason and request.is_json and request.json:
            reason = request.json.get('reason')
        if not reason:
            reason = 'GRN Reversal'

        return delete_func(
            model=GRNotes, 
            condition=GRNotes.grnotesid == GRNotes_id, 
            pkey=GRNotes_id,
            reason=reason,
            user_info=current_user
        )


@grnotes_api_route.route('/grnget')
class GrnWithOUtJoins(Resource):
    per_page = 20

    @grnotes_api_route.marshal_with(grnotes_list_response)
    @grnotes_api_route.doc(params=list_api_params)
    @grnotes_api_route.doc(params=search_params)
    @login_required(permissions='grnote.list')
    def get(self):
        """
        List of grn_mast with pagination
        TODO: Search grn
        :return:
        """
        query = GRNotes.query.order_by(GRNotes.created_on.desc())
        is_moved = request.args.get('moved_items')
        grn_type = request.args.get('search')
        grn_notes = request.args.get('grn_notes')
        if is_moved and is_moved == "UNMOVED":  # it shows only unmoved prod
            query = query.filter(GRNotes.is_moved.isnot(True))
        if is_moved and is_moved == 'MOVED':  # if shows only the moved prod
            query = query.filter(GRNotes.is_moved.isnot(False))
        if grn_type:
            query = query.filter_by(grn_type=grn_type)
        if grn_notes:
            query = query.filter_by(type=grn_notes)
        response = ipss_db.paginated_results(
            model=GRNotes,
            query=query,
            primary_key=primary_key
        )
        return response
