import datetime
import json
from audioop import error

from flask import request
from flask_restx import Resource, marshal
from ipss_utils.decorators import login_required
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, update, bindparam
from sqlalchemy.exc import SQLAlchemyError
from .errorhandling import map_sqlalchemy_error_to_http_status
# from joborder.app.api_doc import items
from .. import ipss_db, db_client
from ipss_utils.ipss_api_doc import list_api_params
from .helper import update_purchase_order, delete_func, update_po_status
from ..api_doc import grnotes_list_request, search_params, qc_search
from ..models.qc import GRNotes, GRNLineItems, QualityAttributesConfig, GrnQcMeasurements

from ..routes.grnotes import qc_api_route, grnotes_list_response, create_grnotes_response, \
    update_grnotes_model, update_grnotes_response, grnotes_get_response, grnotes_bulk_list_response, items_model, \
    grnline_model, grnotes_fields, qc_get_model
from ..routes.grnotes import create_grnotes_model, get_grnotes_response

# Primary key name
primary_key = 'grnotesid'


@qc_api_route.route('/')
class GRN(Resource):
    per_page = 20

    @qc_api_route.marshal_with(grnotes_get_response)
    @qc_api_route.doc(params=grnotes_list_request)
    @login_required(permissions='quality_check.list||Returns.list||InventoryReturns.list')
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
        status = request.args.get('status', None)
        is_moved = request.args.get('is_moved', None)
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
        if status:
            if status == 'Moved to QC':
                sql_condition += "grnotes.status IN ('Moved to QC', 'Partially QC Done') AND "
            else:
                sql_condition += 'grnotes.status=:status and '
        if is_moved:
            sql_condition += ' grnotes.is_moved=:is_moved and '

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
                     # "COALESCE(grnotes.joborderid, jo.joborderno) AS joborderno,"
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
                     "grnotes.return_date as return_date,"
                     "grnotes.vehicle_number as vehicle_number,"
                     "grnotes.driver_name as driver_name,"
                     "grnotes.driver_number as driver_number,"
                     "grnotes.type as type,"
                     "grnotes.created_on as created_on,"
                     "grnotes.created_by as created_by,"
                     "grnotes.modified_on as modified_on,"
                     "grnotes.modified_by as modified_by,"
                     "grnotes.deleted as deleted,"
                     "grnotes.deleted_at as deleted_at,"
                     "grnotes.compcode as compcode, "
                     "grnotes.status as status, "
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
        sql_count = text(f'''select count(distinct grnotesid) 
                     FROM grnotes 
                     LEFT JOIN joborder as jo ON grnotes.joborderid = CAST(jo.joborderid as VARCHAR) 
                     LEFT JOIN vendor as v ON grnotes.vendorid = v.vendorid 
                     WHERE grnotes.compcode = :compcode AND grnotes.deleted = 'false' AND {sql_condition} {types} 1=1 ''')
        sql_count = query_to_dict(db_client.engine.execute(
            sql_count,
            compcode=ccode,
            grnotesid=grnotesid,
            is_moved=is_moved,
            type=type,
            status=status))
        results = query_to_dict(db_client.engine.execute(
            query,
            compcode=ccode,
            grnotesid=grnotesid,
            type=type,
            is_moved=is_moved,
            limit=results_per_page,
            offset=offset,
            status=status
        ))
        for row in results:
            if row.get('status') == 'QC Completed' or row.get('is_moved') is True:
                row['is_qc_done'] = True
                if not row.get('status') or row.get('status') == 'Moved to QC':
                    row['status'] = 'QC Completed'

        return {
            'primary_key': primary_key,
            'total_results': sql_count[0].get('count') if sql_count else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': results
        }

    @login_required(permissions='quality_check.add||Returns.add||InventoryReturns.add')
    @qc_api_route.expect(items_model)
    @qc_api_route.marshal_with(create_grnotes_response)
    def post(self):
        """
        Create GRNotes record and return inserted id
        :return:
        """
        data = request.json
        items = data.pop('items', None)
        cur = request.args.get('current_user', {})
        ccode = cur.get('company_id', None)
        # if data.get("type", None):
        #     data = ipss_db.generate_doc_id(data=data, tx_name='GRN', doc_id_field="grn_no")
        error = ''
        try:
            # Perform the bulk update
            with db_client.session.begin():
                result = ipss_db.insert_record(
                    model=GRNotes,
                    values=data,
                    commit=False
                )
                compcode = request.args.get('current_user', {})
                cc = {"compcode": compcode.get('company_id'),
                      "created_on": datetime.datetime.now(),
                      'grnotesid': result.get('primary_key_id')[0]
                      }
                joline_ids = set()
                for i in items:
                    i.update(**cc)
                    joline_ids.add(i.get('purchase_items_id', None))

                db_client.session.bulk_insert_mappings(mapper=GRNLineItems, mappings=items)
                db_client.engine.execute(update_purchase_order(), items)
                query1 = text('''
                    select distinct jo_id from joline_items 
                    where id in :joline_ids
                    ''')
                jo_id = query_to_dict(db_client.engine.execute(query1, joline_ids=joline_ids))
                db_client.engine.execute(update_po_status(), jo_id)

        except SQLAlchemyError as e:
            error = str(e)
            db_client.session.flush()
            db_client.session.rollback()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': True if not error else False,
            'message': 'Records created successfully' if not error else 'There is an error',
            'error': error
        }


@qc_api_route.route('/<GRNotes_id>/')
class UsersUpdateApi(Resource):
    @staticmethod
    def update_record(data, GRNotes_id):
        data.pop(primary_key, None)
        is_moved = data.get('is_moved', None)
        compcode = request.args.get('current_user', {}).get('company_id')
        if is_moved == 'true':
            query = text('''
            UPDATE joborder j
            SET is_done = true
            WHERE j.compcode =:compcode
            AND j.joborderid = (
                SELECT g.joborderid::integer
                FROM grnotes g
                WHERE g.grnotesid =:grnotesid
                AND g.compcode =:compcode
                AND g.joborderid ~ '^[0-9]+$'
            )
            AND NOT EXISTS (
                SELECT 1
                FROM joline_items jl
                WHERE jl.compcode = j.compcode
                AND jl.jo_id = j.joborderid
                AND COALESCE(jl.quantity_delivered, 0) < COALESCE(jl.quandity, 0)
            )
            ''')
            db_client.session.execute(query,
                                     {"compcode": compcode,
                                      "grnotesid": GRNotes_id})
        result = ipss_db.update_record(
            model=GRNotes,
            condition=GRNotes.grnotesid == GRNotes_id,
            values=data
        )
        return result

    @qc_api_route.marshal_with(items_model)
    @login_required(permissions='quality_check.view||Returns.view||InventoryReturns.view||GoodsNote.edit')
    def get(self, GRNotes_id):
        """
        Read GRNotes record / single record
        :param GRNotes:
        :return:
        """
        ccode = request.args.get('current_user').get('company_id')
        user = GRNotes.query.filter_by(grnotesid=GRNotes_id).first()
        # line = GRNLineItems.query.filter_by(grnotesid=GRNotes_id).all()

        query = text('''
        select gln.*,p.product_name,p.sku_id,p.product_code,p.uom_id,u.uom,jli.quandity,jli.quantity_delivered,p.is_serializable,p.serialization_params,
               jli.lot_no, jli.product_details
        from grnlineitems as gln 
        left join products as p on gln.product_id = p.product_id
        left join uom as u on u.id = p.uom_id 
		left join joline_items as jli on gln.purchase_items_id = jli.id
        where gln.deleted is not true and gln.grnotesid=:grnotesid
        ''')
        items = query_to_dict(db_client.engine.execute(query, grnotesid=GRNotes_id, ccode=ccode))
        for item in items:
            serials_query = text('''
                select serial_number, qc_readings 
                from public.grn_item_serials 
                where grnotesid = :grnotesid and product_id = :product_id and deleted is not true
            ''')
            serials_res = db_client.engine.execute(serials_query, grnotesid=GRNotes_id, product_id=item.get('product_id'))
            
            import json
            serial_list = []
            for row in serials_res.fetchall():
                sn, qc_readings = row[0], row[1]
                if qc_readings:
                    if isinstance(qc_readings, str):
                        serial_list.append(json.loads(qc_readings))
                    else:
                        serial_list.append(qc_readings)
                else:
                    serial_list.append(sn)
            item['serial_numbers'] = serial_list

            # If parent GRN is already completed or moved to store, legacy items are QC completed
            if user and (user.status == 'QC Completed' or user.is_moved or user.is_qc_done):
                item['is_qc_done'] = True
                item['qc_status'] = 'COMPLETED'
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

    @qc_api_route.expect(items_model)
    @qc_api_route.marshal_with(update_grnotes_response)
    @login_required(permissions='quality_check.edit||Returns.edit||InventoryReturns.edit')
    def put(self, GRNotes_id):
        """
        Update GRNLINE Items bulk patch.
        When is_qc_done=True, auto-inserts rejected_material rows for any
        item where damaged_quantity > 0, using action + store_id from payload.
        """
        data = request.json

        items = data.pop('items', None)
        data.pop('grnotes_id', None)
        is_qc_done = data.get('is_qc_done', False)
        cur = request.args.get('current_user', {})
        compcode = cur.get('company_id')
        username = cur.get('username')
        joline_id = set()
        s = db_client.session
        try:
            if data:
                valid_grn_cols = {c.name for c in GRNotes.__table__.columns}
                cleaned_data = {k: v for k, v in data.items() if k in valid_grn_cols}
                if cleaned_data:
                    que = (update(GRNotes).where(GRNotes.grnotesid == GRNotes_id).values(cleaned_data))
                    s.execute(que)
            if items:
                update_data = []
                post_data = []
                for item in items:
                    if 'grnlineid' in item:
                        serials = item.pop('serial_numbers', None)
                        # Set item level qc status if inspected
                        item_is_qc_done = item.get('is_qc_done')
                        if item_is_qc_done is None:
                            # Fallback: if root is_qc_done is true or non_damaged/damaged given, mark done
                            item_is_qc_done = is_qc_done or (item.get('non_damaged_quantity') is not None)
                        item['is_qc_done'] = bool(item_is_qc_done)
                        item['qc_status'] = 'COMPLETED' if item_is_qc_done else 'PENDING'

                        update_data.append(item)
                        if serials is not None:
                            s.execute(text('''
                                delete from public.grn_item_serials 
                                where grnotesid = :grnotesid and product_id = :product_id
                            '''), {'grnotesid': GRNotes_id, 'product_id': item.get('product_id')})
                            for unit in serials:
                                if isinstance(unit, str):
                                    serial_val = unit.strip()
                                    qc_data = None
                                elif isinstance(unit, dict):
                                    serial_key = next((k for k in unit.keys() if k.lower() in ('serial_number', 'serial no', 'serial number', 'serial_no')), None)
                                    serial_val = str(unit[serial_key]).strip() if serial_key else str(list(unit.values())[0]).strip()
                                    qc_data = json.dumps(unit)
                                else:
                                    continue
                                if serial_val:
                                    s.execute(text('''
                                        insert into public.grn_item_serials (grnotesid, product_id, serial_number, qc_readings, compcode)
                                        values (:grnotesid, :product_id, :serial_number, :qc_readings, :compcode)
                                    '''), {
                                        'grnotesid': GRNotes_id,
                                        'product_id': item.get('product_id'),
                                        'serial_number': serial_val,
                                        'qc_readings': qc_data,
                                        'compcode': compcode
                                    })
                        if item.get('purchase_items_id') and item.get('is_qc_done'):
                            fun = update_purchase_order()
                            s.execute(fun, {'non_damaged_quantity': item.get('non_damaged_quantity'),
                                                     'purchase_items_id': item.get('purchase_items_id')})
                            joline_id.add(item.get('purchase_items_id'))
                    else:
                        item.update({'grnotesid': GRNotes_id})
                        post_data.append(item)

                valid_cols = {c.name for c in GRNLineItems.__table__.columns}
                if update_data:
                    for item in update_data:
                        line_id = item.get('grnlineid')
                        cleaned = {k: v for k, v in item.items() if k in valid_cols and k != 'grnlineid'}
                        if cleaned and line_id:
                            s.execute(
                                update(GRNLineItems).where(GRNLineItems.grnlineid == line_id).values(cleaned)
                            )
                if post_data:
                    cleaned_posts = [{k: v for k, v in item.items() if k in valid_cols} for item in post_data]
                    s.bulk_insert_mappings(mapper=GRNLineItems, mappings=cleaned_posts)

                # Flush line updates so subsequent raw SQL queries see the updated rows
                s.flush()

                if joline_id:
                    query1 = text('''
                                select distinct jo_id from joline_items 
                                where id in :joline_ids
                                ''').bindparams(bindparam('joline_ids', expanding=True))
                    jo_rows = s.execute(query1, {'joline_ids': list(joline_id)}).mappings().all()
                    for jo_row in jo_rows:
                        if jo_row and jo_row.jo_id:
                            s.execute(update_po_status(), {'jo_id': jo_row.jo_id})

                # ── Recalculate GRN overall QC status based on all line items ──
                all_lines = s.execute(
                    text("SELECT is_qc_done FROM grnlineitems WHERE grnotesid = :grnotesid AND deleted IS NOT TRUE"),
                    {'grnotesid': GRNotes_id}
                ).fetchall()
                if all_lines:
                    all_done = all(bool(row[0]) for row in all_lines)
                    any_done = any(bool(row[0]) for row in all_lines)
                    if all_done:
                        s.execute(
                            text("UPDATE grnotes SET is_qc_done = TRUE, status = 'QC Completed' WHERE grnotesid = :grnotesid AND compcode = :compcode"),
                            {'grnotesid': GRNotes_id, 'compcode': compcode}
                        )
                    elif any_done:
                        s.execute(
                            text("UPDATE grnotes SET is_qc_done = FALSE, status = 'Partially QC Done' WHERE grnotesid = :grnotesid AND compcode = :compcode"),
                            {'grnotesid': GRNotes_id, 'compcode': compcode}
                        )

            # ── Auto-insert rejected material records ─────────────────────
            if items:
                # Get max existing sequence number for unique_id generation
                count_q = text(
                    "SELECT COALESCE(MAX(SUBSTRING(unique_id FROM '([0-9]+)$')::integer), 0) AS max_seq FROM rejected_material WHERE compcode=:compcode"
                )
                count_res = s.execute(count_q, {'compcode': compcode}).fetchone()
                next_seq = int(count_res.max_seq if count_res and count_res.max_seq is not None else 0)

                for item in items:
                    if not item.get('is_qc_done'):
                        continue
                    damaged_qty = item.get('damaged_quantity') or 0
                    if float(damaged_qty) > 0:
                        grnlineid = item.get('grnlineid')
                        existing_rej = None
                        if grnlineid:
                            existing_rej = s.execute(
                                text("SELECT id FROM rejected_material WHERE grnlineid = :grnlineid AND compcode = :compcode LIMIT 1"),
                                {'grnlineid': grnlineid, 'compcode': compcode}
                            ).fetchone()

                        if existing_rej:
                            update_rej_q = text('''
                                UPDATE rejected_material
                                SET rejected_quantity = :rejected_quantity,
                                    rejection_reason = :rejection_reason,
                                    rejection_remark = :rejection_remark,
                                    image_attachment = :image_attachment,
                                    action = :action,
                                    store_id = :store_id
                                WHERE id = :id
                            ''')
                            s.execute(update_rej_q, {
                                'id': existing_rej.id if hasattr(existing_rej, 'id') else existing_rej[0],
                                'rejected_quantity': float(damaged_qty),
                                'rejection_reason':  json.dumps(item.get('reason') or {}),
                                'rejection_remark':  item.get('remark'),
                                'image_attachment':  json.dumps(item.get('image_attachment') or {}),
                                'action':            item.get('rejection_action', 'Return to Store'),
                                'store_id':          item.get('rejection_store_id'),
                            })
                        else:
                            next_seq += 1
                            unique_id = f"RJT-{str(next_seq).zfill(6)}"
                            insert_q = text('''
                                INSERT INTO rejected_material (
                                    unique_id, grnotesid, grnlineid,
                                    product_id, rejected_quantity,
                                    rejection_reason, rejection_remark,
                                    image_attachment,
                                    action, store_id,
                                    status, compcode,
                                    created_on, created_by
                                )
                                VALUES (
                                    :unique_id, :grnotesid, :grnlineid,
                                    :product_id, :rejected_quantity,
                                    :rejection_reason, :rejection_remark,
                                    :image_attachment,
                                    :action, :store_id,
                                    'Pending', :compcode,
                                    NOW(), :created_by
                                )
                                ON CONFLICT DO NOTHING
                            ''')
                            s.execute(insert_q, {
                                'unique_id':         unique_id,
                                'grnotesid':         GRNotes_id,
                                'grnlineid':         grnlineid,
                                'product_id':        item.get('product_id'),
                                'rejected_quantity': float(damaged_qty),
                                'rejection_reason':  json.dumps(item.get('reason') or {}),
                                'rejection_remark':  item.get('remark'),
                                'image_attachment':  json.dumps(item.get('image_attachment') or {}),
                                'action':            item.get('rejection_action', 'Return to Store'),
                                'store_id':          item.get('rejection_store_id'),
                                'compcode':          compcode,
                                'created_by':        username,
                            })

            s.commit()
        except Exception as e:
            import traceback
            traceback.print_exc()
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)

        return {'success': True,
                'message': 'Bulk update successful'}, 200

    @qc_api_route.expect(update_grnotes_model)
    @qc_api_route.marshal_with(update_grnotes_response)
    @login_required(permissions='quality_check.edit||Returns.edit||InventoryReturns.edit')
    def patch(self, GRNotes_id):
        """
        Partial Update GRNotes record
        :return:
        """
        data = request.json
        response = self.update_record(data, GRNotes_id)
        print("vendor", response)
        return response

    @qc_api_route.marshal_with(update_grnotes_response)
    @login_required(permissions='quality_check.edit||Returns.delete||InventoryReturns.delete')
    def delete(self, GRNotes_id):
        """
        Soft delete GRNotes record
        TODO: Make soft delete
        :return:
        """
        return delete_func(model=GRNotes, condition=GRNotes.grnotesid == GRNotes_id, pkey=GRNotes_id)


@qc_api_route.route('/grnget')
class GrnWithOUtJoins(Resource):
    per_page = 20

    @qc_api_route.marshal_with(grnotes_list_response)
    @qc_api_route.doc(params=list_api_params)
    @qc_api_route.doc(params=search_params)
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


@qc_api_route.route('/report')
class QCReport(Resource):

    @qc_api_route.marshal_with(qc_get_model)
    @qc_api_route.doc(params=qc_search)
    @qc_api_route.doc(params=list_api_params)
    @login_required(permissions='qc_report.list')
    def get(self):

        compcode = request.args.get('current_user').get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page

        product_id = request.args.get('product_id', None)
        grnotesid = request.args.get('grnotesid', None)
        vendorid = request.args.get('vendorid', None)
        reason = request.args.get('reason', None)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        joborderid = request.args.get('joborderid', None)

        sql_con = ''

        if product_id:
            sql_con += ' and p.product_id=:product_id '
        if grnotesid:
            sql_con += 'and grn.grnotesid=:grnotesid '
        if vendorid:
            sql_con += 'and v.vendorid=:vendorid '
        if reason:
            sql_con += ' and (gli.reason->>:reason)::bool is true'
        if joborderid:
            sql_con += ' and jb.joborderid=:joborderid '
        if start_date:
            sql_con += ' and grn.created_on::date between :start_date '
            if end_date:
                sql_con += ' and :end_date '
            else:
                sql_con += ' and :start_date '

        query = text(f'''  
            select grn.grn_no,
            v.companyname,
            jb.joborderno,
            grn.grnotesid,
            grn.grndate,
            grn.created_on,
            json_agg(
                json_build_object(
                    'product_id',p.product_id,
                    'product_code',p.product_code,
                    'sku_id',p.sku_id,
                    'received_quantity',gli.received_quantity,
                    'damaged_quantity',gli.damaged_quantity,
                    'uom',uom.uom,
                    'reason',gli.reason,
                    'remark',gli.remark,
                    'image_attachment',gli.image_attachment
                )
            ) as items
            from grnotes as grn 
            left join grnlineitems as gli on grn.grnotesid = gli.grnotesid
            left join products as p on p.product_id = gli.product_id
            left join uom on uom.id =p.uom_id 
            left join joborder as jb on jb.joborderid::varchar = grn.joborderid
            left join vendor as v on v.vendorid = jb.vendorid 
            where grn.is_moved is true and grn.compcode =:compcode
            {sql_con}
            group by grn.grn_no,v.companyname,jb.joborderno,grn.grnotesid,grn.grndate,grn.created_on
            limit :limit offset :offset
        ''')

        sql_count = text(f'''
            select count(distinct grn.grn_no)
            from grnotes as grn 
            left join grnlineitems as gli on grn.grnotesid = gli.grnotesid
            left join products as p on p.product_id = gli.product_id
            left join joborder as jb on jb.joborderid::varchar = grn.joborderid
            left join vendor as v on v.vendorid = jb.vendorid 
            where grn.is_moved is true and grn.compcode =:compcode
            {sql_con}
        ''')

        result = query_to_dict(db_client.engine.execute(query,
                                                        compcode=compcode,
                                                        start_date=start_date,
                                                        end_date=end_date,
                                                        vendorid=vendorid,
                                                        product_id=product_id,
                                                        grnotesid=grnotesid,
                                                        reason=reason,
                                                        joborderid=joborderid,
                                                        limit=results_per_page,
                                                        offset=offset
                                                        ))

        sql_count = query_to_dict(db_client.engine.execute(sql_count,
                                                           compcode=compcode,
                                                           start_date=start_date,
                                                           end_date=end_date,
                                                           vendorid=vendorid,
                                                           product_id=product_id,
                                                           grnotesid=grnotesid,
                                                           reason=reason,
                                                           joborderid=joborderid
                                                           ))

        return {
            'total_results': sql_count[0].get('count') if sql_count else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': result
        }

@qc_api_route.route('/config')
class QCConfig(Resource):
    @login_required()
    def get(self):
        compcode = request.args.get('compcode')
        if not compcode:
            current_user = request.args.get('current_user') or {}
            compcode = current_user.get('company_id')
        
        if not compcode:
            return {'success': False, 'message': 'compcode is required'}, 400
            
        configs = QualityAttributesConfig.query.filter_by(compcode=compcode).order_by(QualityAttributesConfig.id.desc()).all()
        return {
            'success': True,
            'results': [c.to_dict() for c in configs]
        }

    @login_required()
    def post(self):
        data = request.json
        current_user = request.args.get('current_user') or {}
        compcode = data.get('compcode') or current_user.get('company_id')
        
        if not compcode:
            return {'success': False, 'message': 'compcode is required'}, 400

        config_id = data.get('id')
        if config_id:
            # Update existing
            config_item = QualityAttributesConfig.query.get(config_id)
            if config_item:
                config_item.customer_id = data.get('customer_id')
                config_item.raw_material_id = data.get('raw_material_id')
                config_item.attribute_name = data.get('attribute_name')
                config_item.attribute_type = data.get('attribute_type', 'boolean')
                config_item.min_value = data.get('min_value')
                config_item.max_value = data.get('max_value')
                db_client.session.commit()
                return {'success': True, 'message': 'Config updated successfully', 'id': config_item.id}
        
        # Create new
        new_config = QualityAttributesConfig(
            compcode=compcode,
            customer_id=data.get('customer_id'),
            raw_material_id=data.get('raw_material_id'),
            attribute_name=data.get('attribute_name'),
            attribute_type=data.get('attribute_type', 'boolean'),
            min_value=data.get('min_value'),
            max_value=data.get('max_value')
        )
        db_client.session.add(new_config)
        db_client.session.commit()
        
        return {'success': True, 'message': 'Config created successfully', 'id': new_config.id}

@qc_api_route.route('/config/<int:id>')
class QCConfigDetail(Resource):
    @login_required()
    def delete(self, id):
        config_item = QualityAttributesConfig.query.get(id)
        if not config_item:
            return {'success': False, 'message': 'Config not found'}, 404
            
        db_client.session.delete(config_item)
        db_client.session.commit()
        return {'success': True, 'message': 'Config deleted successfully'}

@qc_api_route.route('/specs')
class QCSpecsResolver(Resource):
    @login_required()
    def get(self):
        raw_material_id = request.args.get('raw_material_id')
        joborderid = request.args.get('joborderid')
        customer_id = request.args.get('customer_id')
        compcode = request.args.get('compcode')
        
        if not compcode:
            current_user = request.args.get('current_user') or {}
            compcode = current_user.get('company_id')

        if not raw_material_id or not compcode:
            return {'success': False, 'message': 'raw_material_id and compcode are required'}, 400

        # If joborderid is provided but customer_id is not, resolve customer_id from Job Order
        if joborderid and not customer_id:
            try:
                # Query joborder table to get customer_id
                query = text("SELECT customer_purchase_id FROM joborder WHERE joborderid = :jo_id LIMIT 1")
                res = db_client.engine.execute(query, jo_id=joborderid).fetchone()
                if res and res[0]:
                    customer_id = res[0]
            except Exception as e:
                print("Error resolving customer from joborder:", e)

        # Build fallback spec query
        # Priority 1: Customer specific for this material
        # Priority 2: Material specific default
        # Priority 3: Global defaults (where customer_id is null and raw_material_id is null)
        
        # Load all configs for the company
        configs = QualityAttributesConfig.query.filter_by(compcode=compcode).all()
        
        # Filter matching specs
        matched_specs = []
        
        # 1. Customer-material specific
        if customer_id:
            matched_specs = [c for c in configs if c.customer_id == int(customer_id) and c.raw_material_id == int(raw_material_id)]
            
        # 2. Fallback to material-specific default
        if not matched_specs:
            matched_specs = [c for c in configs if c.customer_id is None and c.raw_material_id == int(raw_material_id)]
            
        # 3. Fallback to global defaults
        if not matched_specs:
            matched_specs = [c for c in configs if c.customer_id is None and c.raw_material_id is None]
            
        return {
            'success': True,
            'results': [s.to_dict() for s in matched_specs]
        }


@qc_api_route.route('/pending-products')
class QCPendingProducts(Resource):
    @staticmethod
    def _serialize(row):
        from decimal import Decimal
        import datetime
        row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
        result = {}
        for k, v in row_dict.items():
            if isinstance(v, Decimal):
                result[k] = float(v)
            elif isinstance(v, (datetime.datetime, datetime.date)):
                result[k] = v.isoformat()
            else:
                result[k] = v
        return result

    @login_required()
    def get(self):
        """
        Get all distinct products that have pending QC in GRNs
        """
        current_user = request.args.get('current_user') or {}
        compcode = current_user.get('company_id')
        if not compcode:
            return {'success': False, 'message': 'Company code not found'}, 400

        query = text("""
            SELECT 
                p.product_id, 
                p.product_name, 
                p.sku_id, 
                p.product_code, 
                u.uom,
                COUNT(gli.grnlineid) as pending_lots_count,
                SUM(COALESCE(gli.received_quantity, 0)) as total_received_quantity
            FROM grnlineitems gli
            JOIN grnotes ON gli.grnotesid = grnotes.grnotesid
            JOIN products p ON gli.product_id = p.product_id
            LEFT JOIN uom u ON p.uom_id = u.id
            WHERE grnotes.compcode = :compcode
              AND (grnotes.deleted IS NOT TRUE OR grnotes.deleted = 'false')
              AND (gli.deleted IS NOT TRUE OR gli.deleted = 'false')
              AND grnotes.status IN ('Moved to QC', 'Partially QC Done')
              AND COALESCE(gli.is_qc_done, FALSE) = FALSE
            GROUP BY p.product_id, p.product_name, p.sku_id, p.product_code, u.uom
            ORDER BY p.product_name ASC
        """)
        try:
            with db_client.engine.connect() as conn:
                result = conn.execute(query.bindparams(compcode=compcode))
                results = [self._serialize(row) for row in result]
            return {'success': True, 'results': results}
        except Exception as e:
            print('Error in /pending-products:', e)
            db_client.session.rollback()
            return {'success': False, 'message': str(e)}, 500


@qc_api_route.route('/pending-items-by-product')
class QCPendingItemsByProduct(Resource):
    @login_required()
    def get(self):
        """
        Get all pending GRN line items for a specific product
        """
        product_id = request.args.get('product_id')
        current_user = request.args.get('current_user') or {}
        compcode = current_user.get('company_id')
        if not compcode:
            return {'success': False, 'message': 'Company code not found'}, 400
        if not product_id:
            return {'success': False, 'message': 'product_id is required'}, 400

        try:
            product_id_val = int(product_id)
        except (ValueError, TypeError):
            return {'success': False, 'message': 'Invalid product_id'}, 400

        query = text("""
            SELECT 
                gli.grnlineid,
                gli.grnotesid,
                gli.product_id,
                gli.product_name,
                gli.received_quantity,
                gli.non_damaged_quantity,
                gli.damaged_quantity,
                gli.supplier_lot_no,
                gli.reason,
                gli.remark,
                gli.is_qc_done,
                gli.qc_status,
                gli.purchase_items_id,
                grnotes.grn_no,
                grnotes.grndate,
                grnotes.deliverychallan_no,
                grnotes.inviceno,
                grnotes.vendorid,
                grnotes.status as grn_status,
                v.companyname as vendor_name,
                p.sku_id,
                p.product_code,
                u.uom,
                jli.lot_no as target_lot_number,
                jli.product_details
            FROM grnlineitems gli
            JOIN grnotes ON gli.grnotesid = grnotes.grnotesid
            JOIN products p ON gli.product_id = p.product_id
            LEFT JOIN uom u ON p.uom_id = u.id
            LEFT JOIN vendor v ON grnotes.vendorid = v.vendorid
            LEFT JOIN joline_items jli ON gli.purchase_items_id = jli.id
            WHERE grnotes.compcode = :compcode
              AND gli.product_id = :product_id
              AND (grnotes.deleted IS NOT TRUE OR grnotes.deleted = 'false')
              AND (gli.deleted IS NOT TRUE OR gli.deleted = 'false')
              AND grnotes.status IN ('Moved to QC', 'Partially QC Done')
              AND COALESCE(gli.is_qc_done, FALSE) = FALSE
            ORDER BY grnotes.created_on DESC
        """)
        try:
            with db_client.engine.connect() as conn:
                result = conn.execute(query.bindparams(compcode=compcode, product_id=product_id_val))
                results = [QCPendingProducts._serialize(row) for row in result]
            return {'success': True, 'results': results}
        except Exception as e:
            print('Error in /pending-items-by-product:', e)
            db_client.session.rollback()
            return {'success': False, 'message': str(e)}, 500

