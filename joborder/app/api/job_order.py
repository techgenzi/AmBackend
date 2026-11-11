
import datetime
from collections import defaultdict

from ipss_utils.redis.ipss_redis import query_to_dict
from sqlalchemy.dialects.mysql import NUMERIC

from .errorhandling import map_sqlalchemy_error_to_http_status, update_local
# from joborder.app import ipss_db,db_client
from .. import db_client, ipss_db
from sqlalchemy.exc import SQLAlchemyError
from flask import request, jsonify
from flask_restx import Resource, abort
from ipss_utils.decorators import login_required
from sqlalchemy import text, insert, update
from .. import db_client
from ..api_doc import search_types, joborder_report, product_price_filter
from ..models.job_order import Joborder, JobOrderLineItems, SeqGenerate, InternalSequence
from ..routes.job_order_school import job_order_api_route, job_order_get_all_model, \
    create_job_order_response, \
    update_job_order_model, update_job_order_response, job_order_model, job_order_report_model, \
    product_price_list_response, amendment_log_response
from ..routes.job_order_school import create_job_order_model, get_job_order_response,job_order_get_all_model
# Primary key name
primary_key = 'joborderid'


def get_po_sequence(s=db_client.session, type='purchase_order'):
    current_user = request.args.get('current_user', {})
    company_id = current_user.get('company_id')

    query = text('''
        select * from seqgenerate
        where product_group =:type and compcode =:compcode
    ''')

    result = query_to_dict(db_client.engine.execute(query,
                                                    type=type,
                                                    compcode=str(company_id)))
    sequence_num = None
    try:
        if True if result else False:
            prefix = result[0].get('prefix')
            last_no = result[0].get('lastno')
            zeropading = result[0].get('zeropadding')
            next_no = int(last_no)+1
            formatnum = str(next_no).zfill(zeropading)
            sequence_num = f"{prefix}{formatnum}"

            update_data = {'lastno': next_no}
            condition = SeqGenerate.seqgenerateid == result[0].get('seqgenerateid')
            update_local(model=SeqGenerate, s=s, condition=condition,values=update_data, commit=False)
        else:
            query = text('''
                            select count(*) from joborder where compcode=:compcode and type=:type
                            ''')
            result = query_to_dict(db_client.engine.execute(query,
                                                            type=type,
                                                            compcode=company_id))
            count = result[0].get('count', 0) if result else 0
            next_no = int(count) + 1
            formatnum = str(int(next_no)).zfill(6)
            if type == 'purchase_order':
                sequence_num = f"PO-{formatnum}"
            else:
                sequence_num = f"JO-{formatnum}"

    except Exception as e:
        print("In po seq except block", e)
        s.rollback()
        return map_sqlalchemy_error_to_http_status(e)

    return sequence_num


def get_customer_po_seq(s=db_client.session, type='purchase_order'):
    current_user = request.args.get('current_user', {})
    company_id = current_user.get('company_id')

    query = text('''
        select * from customersequence
        where product_group =:type and compcode =:compcode
    ''')

    result = query_to_dict(db_client.engine.execute(query,
                                                    type=type,
                                                    compcode=company_id))
    sequence_num = None
    try:
        if result:
            prefix = result[0].get('prefix')
            acc_year = result[0].get('acc_year')
            last_no = result[0].get('lastno')
            zeropading = result[0].get('zeropadding')
            next_no = int(last_no)+1
            formatnum = str(next_no).zfill(zeropading)
            sequence_num = f"{prefix}{acc_year}{formatnum}"

            update_data = {'lastno': next_no}
            condition = InternalSequence.id == result[0].get('id')
            update_local(model=InternalSequence, s=s, condition=condition, values=update_data, commit=False)
    except Exception as e:
        s.rollback()
        return ""

    return sequence_num

def json_diff(old, new):
    diff = {}

    all_keys = set(old.keys()) | set(new.keys())

    for key in all_keys:
        old_val = old.get(key)
        new_val = new.get(key)

        if isinstance(old_val, dict) and isinstance(new_val, dict):
            nested_diff = json_diff(old_val, new_val)
            if nested_diff:
                diff[key] = nested_diff

        elif old_val != new_val:
            diff[key] = {
                "old": old_val,
                "new": new_val
            }

    return diff

import re

def normalize(val):
    if val is None:
        return None

    from datetime import datetime, date
    from decimal import Decimal

    if isinstance(val, Decimal):
        return float(val)

    if isinstance(val, int):
        return float(val)

    if isinstance(val, datetime):
        return val.isoformat()

    if isinstance(val, dict):
        return {k: normalize(v) for k, v in val.items()}

    if isinstance(val, list):
        return [normalize(v) for v in val]

    # if isinstance(val, datetime.datetime):
    #     return val.strftime("%Y-%m-%d")

    if isinstance(val, date):
        return val.strftime("%Y-%m-%d")

    if isinstance(val, str):
        val = val.strip()

        # ✅ Check if it's a pure integer
        if re.fullmatch(r"-?\d+", val):
            return float(val)

        # ✅ Check if it's a pure float
        if re.fullmatch(r"-?\d+\.\d+", val):
            return float(val)

        # ❌ Otherwise keep as string
        return val

    return val

import json
def amend_log(joborder_id, new_data,s=db_client.session):
    try:
        current_user = request.args.get('current_user', {}) or {}
        username = current_user.get('username', 'system')
        company_id = current_user.get('company_id')
        compare_fields = ["quandity", "rate_per_item", "gst", "total_price", "hsn"]
        old_po = s.execute(
            text("SELECT * FROM joborder WHERE joborderid = :id"),
            {"id": joborder_id}
        ).mappings().first()

        if not old_po:
            raise Exception("PO not found")

        old_po = dict(old_po)

        old_items = s.execute(
            text("SELECT * FROM joline_items WHERE jo_id = :id AND deleted = false"),
            {"id": joborder_id}
        ).mappings().all()

        old_items = [dict(item) for item in old_items]

        old_map = {item["rawmaterialsid"]: item for item in old_items}
        new_items = new_data.get("items", [])
        new_map = {item["rawmaterialsid"]: item for item in new_items}

        old_ids = set(old_map.keys())
        new_ids = set(new_map.keys())

        added = []
        deleted = []
        updated = []

        for rid in new_ids - old_ids:
            added.append({
                "rawmaterialsid": rid,
                "new": normalize(new_map[rid])
            })

        for rid in old_ids - new_ids:
            deleted.append({
                "rawmaterialsid": rid,
                "old": normalize(old_map[rid])
            })

        for rid in old_ids & new_ids:
            old_item = old_map[rid]
            new_item = new_map[rid]

            field_changes = {}

            for field in compare_fields:
                old_val = normalize(old_item.get(field))
                new_val = normalize(new_item.get(field))
                print("Comparing field:", field)
                print("Old value:", old_val, "New value:", new_val, type(old_val), type(new_val))
                if str(old_val) != str(new_val):
                    field_changes[field] = {
                        "old": old_val,
                        "new": new_val
                    }

            if field_changes:
                updated.append({
                    "rawmaterialsid": rid,
                    "fields": field_changes
                })

        header_changes = {}

        for key in ["gst_type", "notes", "termsand_condition", "vendorid", "ordercompletiondate",
                    "jo_valid_date", "jo_date", "joaql", "description", "jo_status"]:
            old_val = normalize(old_po.get(key))
            new_val = normalize(new_data.get(key))
            # print("old_val",key," ",old_po.get(key)," ",old_val)
            # print("new_val",key," ",new_data.get(key)," ",new_val)
            if str(old_val) != str(new_val):
                header_changes[key] = {
                    "old": old_val,
                    "new": new_val
                }

        old_attr = old_po.get("add_attribute") or {}
        new_attr = new_data.get("add_attribute") or {}

        attr_diff = json_diff(old_attr, new_attr)

        if attr_diff:
            header_changes["add_attribute"] = attr_diff

        change_log = {
            "po_id": joborder_id,
            "created_by": username,
            "created_on": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:S"),
            "changes": {
                "header": header_changes,
                "items": {
                    "added": added,
                    "updated": updated,
                    "deleted": deleted
                }
            }
        }
        change_log = normalize(change_log)
        stmt = text("""
            INSERT INTO joborder_amend_log 
            (joborderid, changed_data, created_on, compcode, created_by)
            VALUES 
            (:joborderid, :changed_data, :created_on, :compcode, :created_by)
        """)
        # print("Change log to be inserted:", change_log)
        s.execute(stmt, {
            "joborderid": joborder_id,
            "changed_data": json.dumps(change_log),
            "created_by": username,
            "compcode": company_id,
            "created_on": datetime.datetime.now()
        })

        return {
            'success': True,
            'resposne': change_log
        }

    except Exception as e:
        s.rollback()
        # print("Error in amend_log:", e)
        raise

@job_order_api_route.route('/')
class JobOrder(Resource):

    #per_page = 20
    @job_order_api_route.marshal_with(job_order_get_all_model)
    @job_order_api_route.doc(params=search_types)
    @login_required()
    def get(self):
        """
        List of Job_ORDER with pagination
        TODO: Search Joborder
        :return:
        """
        current_user = request.args.get('current_user')
        compcode = current_user.get('company_id', None)
        emp_id = current_user.get('emp_id')
        sql_condition = ""
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        type = request.args.get('type', None)
        status = request.args.get('status', None)
        joborderno = request.args.get('joborderno', None)
        vendorid = request.args.get('vendorid', None)
        joborderid = request.args.get('joborderid', None)
        is_done = request.args.get('is_done', None)
        customer_purchase_id = request.args.get('customer_purchase_id', None)

        if customer_purchase_id:
            sql_condition += "joborder.customer_purchase_id=:customer_purchase_id AND "
        if type:
            sql_condition += "joborder.type=:type AND"
        if status:
            sql_condition += "joborder.jo_status=:status AND"
        if joborderno:
            joborderno = str(joborderno)
            sql_condition += f"joborder.joborderno=:joborderno AND"
        if joborderid:
            sql_condition += f"joborder.joborderid={joborderid} AND"
        if vendorid:
            sql_condition += f"joborder.vendorid={vendorid} AND "
        if is_done == True:
            sql_condition += 'joborder.is_done is true and '
        if is_done == False:
            sql_condition += 'joborder.is_done is not true and '

        if request.args.get('is_delivered') == 'true':
            # print("sdfedsfedfewd")
            sql_condition += ''' jl.quandity > COALESCE(jl.quantity_delivered,0) and 
            joborder.jo_status='Approved' and 
            '''
            # Assuming vendorid is an integer
        integrated_query = text(f"""
                        SELECT joborder.*,vendor.companyname ,vendor.contactname,
                        COALESCE(SUM(jl.total_price), 0) AS total_value,
                        cp.order_unique,cp.customer_purchase_id,
                        count(*) over() as total_count
                        FROM joborder 
                        left JOIN vendor ON vendor.vendorid = joborder.vendorid
                        left join joline_items jl on jl.jo_id=joborder.joborderid and jl.deleted is not true
                        left join customer_purchase cp on cp.customer_purchase_id=joborder.customer_purchase_id
                        WHERE {sql_condition} 1=1 AND
                        joborder.deleted is not true and joborder.compcode =:compcode
                        group by joborder.joborderid,vendor.companyname ,vendor.contactname,cp.order_unique,cp.customer_purchase_id
                        ORDER BY joborder.created_on DESC
                        LIMIT :limit OFFSET :offset;
                        """)

        results = query_to_dict(
            db_client.engine.execute(integrated_query, limit=results_per_page, offset=offset, vendorid=vendorid,
                                     is_delivered=request.args.get('is_delivered'),
                                     customer_purchase_id=customer_purchase_id,
                                     joborderid=str(joborderid), joborderno=str(joborderno), type=str(type),
                                     status=str(status), compcode=compcode))

        return {"total_results": results[0].get('total_count') if results else 0,
                "page": paged,
                "results_per_page": results_per_page,
                "results": results}

    @login_required()
    @job_order_api_route.expect(create_job_order_model)
    @job_order_api_route.marshal_with(create_job_order_response)
    def post(self):
        """
        Create Job_ORDER record and return inserted id
        :return:
        """
        current_user = request.args.get('current_user')
        ccode = current_user.get('company_id')
        data = request.json
        print(data, "data in post")
        type = data.get('type', None)
        data.pop(primary_key, None)
        items = data.pop('items', None)
        grouped_items = defaultdict(list)

        for item in items:
            vendor_id = item.get('vendorid', None) or data.get('vendorid', None)
            if vendor_id:
                grouped_items[vendor_id].append(item)
        cc = {"compcode": ccode,
              "created_on": datetime.datetime.now(),
              'created_by': current_user.get('username')
              }

        s = db_client.session
        try:
            with s.begin():
                for vendor_id, item in grouped_items.items():
                    data['joborderno'] = get_po_sequence(s, type=type)
                    data['customer_po_no'] = get_customer_po_seq(s, type=type)
                    data['vendorid'] = vendor_id
                    stmt = (
                        insert(Joborder).values(**data, **cc).returning(Joborder.joborderid)
                    )
                    result = s.execute(stmt)
                    primary_key_id = result.scalar()
                    if primary_key_id:
                        if item:
                            itemsdata = [{**i, **cc, **{"jo_id": primary_key_id}} for i in item]
                            s.bulk_insert_mappings(mapper=JobOrderLineItems, mappings=itemsdata)

        except Exception as e:
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': True,
            'message': "Records created Successfully"
        }


@job_order_api_route.route('/<joborder_id>/')
class JobOrderUpdateApi(Resource):

    @staticmethod
    def put_record(data, joborder_id,s=db_client.session):
        data.pop('joborderid', None)
        items = data.pop('items', None)
        success = False
        error = ''
        try:
            old_jo = s.query(Joborder).filter(Joborder.joborderid == joborder_id).first()
            old_status = old_jo.jo_status if old_jo else None

            # with s.begin():
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
            current_ids = set()
            for item in items:
                if item.get('id'):
                    updateitemData.append(
                        {**item, **cc, 'deleted': False})
                else:
                    itemdata.append({**item, **new_cc, "jo_id": joborder_id, "deleted": False})
                if item.get('id'):
                    current_ids.add(item.get('id'))
            existing_records = db_client.session.query(JobOrderLineItems).filter(
                JobOrderLineItems.jo_id == joborder_id,
                JobOrderLineItems.deleted != True
            ).all()

            existing_ids = {record.id for record in existing_records}

            to_delete_ids = existing_ids - current_ids

            #print(to_delete_ids)

            if data:
                stmt = (
                    update(Joborder)
                    .where(Joborder.joborderid == joborder_id)
                    .values(**data)
                )
                db_client.session.execute(stmt)

            if to_delete_ids:
                s.query(JobOrderLineItems).filter(
                    JobOrderLineItems.id.in_(to_delete_ids)
                ).update({"deleted": True}, synchronize_session=False)

            if updateitemData:
                s.bulk_update_mappings(mapper=JobOrderLineItems, mappings=updateitemData)
            if itemdata:
                s.bulk_insert_mappings(mapper=JobOrderLineItems, mappings=itemdata)

            # Check status transition to 'Approved' to issue raw materials
            new_status = data.get('jo_status')
            if new_status == 'Approved' and old_status != 'Approved' and old_jo and old_jo.type == 'job_order':
                add_attr = data.get('add_attribute', {})
                if not add_attr:
                    add_attr = old_jo.add_attribute or {}
                
                store_id = add_attr.get('store_id')
                if not store_id:
                    s.rollback()
                    return abort(400, "Store selection is required to approve the Job Order and issue raw materials.")
                
                # Fetch all active line items of this Job Order after mapping updates
                active_items = s.query(JobOrderLineItems).filter(
                    JobOrderLineItems.jo_id == joborder_id,
                    JobOrderLineItems.deleted != True
                ).all()
                
                for item in active_items:
                    if item.type == 'raw_material':
                        comp_id = item.rawmaterialsid
                        qty_to_issue = item.quandity or 0
                        if not comp_id or qty_to_issue <= 0:
                            continue
                            
                        lot_no = item.lot_no or ''
                        # Deduct from products table
                        upd_prod = text('''
                            UPDATE products 
                            SET product_count = COALESCE(product_count, 0) - :qty
                            WHERE product_id = :prod_id
                        ''')
                        s.execute(upd_prod, {'qty': qty_to_issue, 'prod_id': comp_id})
                        
                        # Deduct from store_product table
                        upd_store = text('''
                            UPDATE store_product 
                            SET product_count = COALESCE(product_count, 0) - :qty
                            WHERE product_id = :prod_id AND store_id = :store_id AND COALESCE(lot_no, '') = :lot_no AND compcode = :ccode AND deleted IS NOT TRUE
                        ''')
                        s.execute(upd_store, {'qty': qty_to_issue, 'prod_id': comp_id, 'store_id': store_id, 'lot_no': lot_no, 'ccode': cc.get('compcode')})
                        
                        # Log outward entry in invregistry
                        ins_registry = text('''
                            INSERT INTO invregistry (
                                product_id, requested_amount, approved_amount, action, ref_id, 
                                status, is_dispatch, store_id, compcode, userid, approval_id, 
                                approval_date, created_on, created_by, type, deleted, lot_no
                            ) VALUES (
                                :product_id, :qty, :qty, 'Outward', :ref_id, 
                                'Approved', true, :store_id, :compcode, :userid, :userid, 
                                NOW(), NOW(), :username, 'JobOrder-Issue', false, :lot_no
                            )
                        ''')
                        s.execute(ins_registry, {
                            'product_id': comp_id,
                            'qty': qty_to_issue,
                            'ref_id': old_jo.joborderno,
                            'store_id': store_id,
                            'compcode': cc.get('compcode'),
                            'userid': compcode.get('userid'),
                            'username': compcode.get('username'),
                            'lot_no': item.lot_no
                        })

            success = True

        except SQLAlchemyError as e:
            error = f"Database error: {str(e)}"
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': success,
            'message': "Update successful" if success else "Error in update",
            'error': error
        }
    @job_order_api_route.marshal_with(job_order_model)
    @login_required()
    def get(self, joborder_id):
        """
        Read Job_order record / single record
        :param joborderid:
        :return:
        """
        query = text(
            '''
        
select 
            jo.joborderid,jo.joborderno,jo.jo_date,jo.jo_valid_date,jo.jo_status,jo.type,jo.vendorid,v.companyname,
            v.contactname,v.emailid,v.mobileno,cp.order_unique,cp.customer_purchase_id,jo.description, jo.termsand_condition,
            jo.gst_type,jo.notes, jo.is_done, jo.jo_aql, jo.ordercompletiondate,v.gstno,v.bill_addline1,
            jo.customer_po_no,
            jo.add_attribute,
            CASE
        WHEN EXISTS (
            SELECT 1
            FROM joborder_amend_log am
            WHERE am.joborderid = jo.joborderid
        ) THEN TRUE
        ELSE FALSE
    END AS is_amendment,
        json_agg(
        json_build_object(
        'id', jli.id,
        'rawmaterialsid', jli.rawmaterialsid,
        'product_name', p.product_name,
        'product_code', p.product_code,
        'sku_id', p.sku_id,
        'uom', u.uom,
        'quandity', jli.quandity,
        'quantity_delivered', jli.quantity_delivered,
        'quantity_ordered', jli.quantity_ordered,
        'rate_per_item', jli.rate_per_item,
        'cgst_sgst', jli.cgst_sgst,
        'gst', jli.gst,
        'igst', jli.igst,
        'notes', jli.notes,
        'description', jli.description,
        'total_price', jli.total_price,
        'type', jli.type,
        'hsn', jli.hsn,
        'lot_no', jli.lot_no,
        'product_details', jli.product_details
        )
        ) as items
        from joborder jo
        left join joline_items jli on jli.jo_id = jo.joborderid
        left join customer_purchase cp on jo.customer_purchase_id = cp.customer_purchase_id 
        left join products p on p.product_id = jli.rawmaterialsid
        left join vendor v on v.vendorid = jo.vendorid
        left join uom u on u.id = p.uom_id
        where jo.joborderid =:joborder_id and jli.deleted is not true
        group by 
        jo.joborderid,jo.joborderno,jo.jo_date,jo.jo_valid_date,jo.jo_status,jo.type,jo.vendorid,v.companyname,
            v.contactname,v.emailid,v.mobileno,cp.order_unique,cp.customer_purchase_id,jo.description, jo.termsand_condition,
            jo.gst_type,jo.notes, jo.is_done, jo.jo_aql, jo.ordercompletiondate,v.gstno,v.bill_addline1,
            jo.customer_po_no,
            jo.add_attribute
            '''
        )
        result = query_to_dict(db_client.engine.execute(query, joborder_id=joborder_id))
        result = result[0] if result else {}

        return result

    @job_order_api_route.expect(update_job_order_model)
    @job_order_api_route.marshal_with(update_job_order_response)
    @login_required()
    def put(self, joborder_id):
        """
        Update Job_ORDER record
        :return:
        """
        data = request.json
        try:
            s = db_client.session
            with s.begin():
                amend_log(s=s,joborder_id=joborder_id, new_data=data)
                response = self.put_record(s=s,data=data, joborder_id=joborder_id)
                return response
        except SQLAlchemyError as e:
            error = f"Database error: {str(e)}"
            return {
                'success': False,
                'message': "Error in update",
                'error': error
            }

    @job_order_api_route.expect(create_job_order_model)
    @job_order_api_route.marshal_with(update_job_order_response)
    @login_required()
    def patch(self, joborder_id):
        """
        Partial Update Job_ORDER record
        :return:
        """
        data = request.json
        s = db_client.session
        try:
            with s.begin():
                old_jo = s.query(Joborder).filter(Joborder.joborderid == joborder_id).first()
                old_status = old_jo.jo_status if old_jo else None

                if data:
                    s.execute(
                        update(Joborder)
                        .where(Joborder.joborderid == joborder_id)
                        .values(**data)
                    )

                # Check status transition to 'Approved' to issue raw materials
                new_status = data.get('jo_status')
                if new_status == 'Approved' and old_status != 'Approved' and old_jo and old_jo.type == 'job_order':
                    add_attr = data.get('add_attribute', {})
                    if not add_attr:
                        add_attr = old_jo.add_attribute or {}
                    
                    store_id = add_attr.get('store_id')
                    if not store_id:
                        s.rollback()
                        return abort(400, "Store selection is required to approve the Job Order and issue raw materials.")
                    
                    compcode = request.args.get('current_user', {})
                    cc = {
                        "compcode": compcode.get('company_id')
                    }
                    
                    # Fetch all active line items of this Job Order
                    active_items = s.query(JobOrderLineItems).filter(
                        JobOrderLineItems.jo_id == joborder_id,
                        JobOrderLineItems.deleted != True
                    ).all()
                    
                    for item in active_items:
                        if item.type == 'raw_material':
                            comp_id = item.rawmaterialsid
                            qty_to_issue = item.quandity or 0
                            if not comp_id or qty_to_issue <= 0:
                                continue
                                
                            lot_no = item.lot_no or ''
                            # Deduct from products table
                            upd_prod = text('''
                                UPDATE products 
                                SET product_count = COALESCE(product_count, 0) - :qty
                                WHERE product_id = :prod_id
                            ''')
                            s.execute(upd_prod, {'qty': qty_to_issue, 'prod_id': comp_id})
                            
                            # Deduct from store_product table
                            upd_store = text('''
                                UPDATE store_product 
                                SET product_count = COALESCE(product_count, 0) - :qty
                                WHERE product_id = :prod_id AND store_id = :store_id AND COALESCE(lot_no, '') = :lot_no AND compcode = :ccode AND deleted IS NOT TRUE
                            ''')
                            s.execute(upd_store, {'qty': qty_to_issue, 'prod_id': comp_id, 'store_id': store_id, 'lot_no': lot_no, 'ccode': cc.get('compcode')})
                            
                            # Log outward entry in invregistry
                            ins_registry = text('''
                                INSERT INTO invregistry (
                                    product_id, requested_amount, approved_amount, action, ref_id, 
                                    status, is_dispatch, store_id, compcode, userid, approval_id, 
                                    approval_date, created_on, created_by, type, deleted, lot_no
                                ) VALUES (
                                    :product_id, :qty, :qty, 'Outward', :ref_id, 
                                    'Approved', true, :store_id, :compcode, :userid, :userid, 
                                    NOW(), NOW(), :username, 'JobOrder-Issue', false, :lot_no
                                )
                            ''')
                            s.execute(ins_registry, {
                                'product_id': comp_id,
                                'qty': qty_to_issue,
                                'ref_id': old_jo.joborderno,
                                'store_id': store_id,
                                'compcode': cc.get('compcode'),
                                'userid': compcode.get('userid'),
                                'username': compcode.get('username'),
                                'lot_no': item.lot_no
                            })

        except Exception as e:
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)

        return {'success': True, 'message': 'Update successful'}

    @job_order_api_route.marshal_with(update_job_order_response)
    @login_required()
    def delete(self, joborder_id):
        """
        Soft delete Job_ORDER record
        TODO: Make soft delete
        :return:
        """
        result = ipss_db.update_record(
            model=Joborder,
            condition=Joborder.joborderid == joborder_id,
            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result



@job_order_api_route.route('/report')
class JobOrderReport(Resource):

    @job_order_api_route.marshal_with(job_order_report_model)
    @job_order_api_route.doc(params=search_types)
    @job_order_api_route.doc(params=joborder_report)
    @login_required()
    # @login_required()
    def get(self):
        current_user = request.args.get('current_user')
        compcode = current_user.get('company_id', None)
        sql_condition = ""
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        type = request.args.get('type', None)
        status = request.args.get('status', None)
        joborderno = request.args.get('joborderno', None)
        vendorid = request.args.get('vendorid', None)
        joborderid = request.args.get('joborderid', None)
        product_id = request.args.get('product_id', None)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        is_done = request.args.get('is_done', None)
        customer_purchase_id = request.args.get('customer_purchase_id', None)
        print(is_done)
        if type:
            sql_condition += " jb.type=:type AND "

        if customer_purchase_id:
            sql_condition += "jb.customer_purchase_id=:customer_purchase_id AND "

        if status:
            sql_condition += " jb.jo_status=:status AND "

        if joborderno:
            joborderno = str(joborderno)
            sql_condition += f" jb.joborderno=:joborderno AND "
        if joborderid:
            sql_condition += f"jb.joborderid={joborderid} AND "
        if vendorid:
            sql_condition += f"jb.vendorid={vendorid} AND "
        if product_id:
            sql_condition += ' jli.rawmaterialsid=:product_id AND '
        if is_done == "true":
            sql_condition += ' jb.is_done is true and '
        elif is_done == "false":
            sql_condition += ' jb.is_done is not true and '
        if start_date:
            sql_condition += ' jb.created_on::date between :start_date '
            if end_date:
                sql_condition += ' and :end_date and '
            else:
                sql_condition += ' and :start_date and '

        if request.args.get('is_delivered') == 'true':
            print("sdfedsfedfewd")
            sql_condition += ''' jl.quandity > COALESCE(jl.quantity_delivered,0) and 
                    joborder.jo_status='Approved' and 
                    '''
        integrated_query = text(f"""        
            select jb.*,vendor.companyname ,vendor.contactname,
            cp.order_unique,cp.customer_purchase_id,
            count(*) over() as total_count,
            jsonb_agg(
            jsonb_set(
           jsonb_set(
               jsonb_set(
                   jsonb_set(
                       row_to_json(jli)::jsonb,
                       '{{product_name}}', 
                       to_jsonb(p.product_name)
                   ),
                   '{{uom}}', 
                   to_jsonb(coalesce(uom.uom,''))
               ),
               '{{product_code}}', 
               to_jsonb(p.product_code)
           ),
           '{{sku_id}}',
           to_jsonb(p.sku_id)
           )
       ) AS items
            from joborder as jb 
            left join joline_items as jli on jb.joborderid = jli.jo_id
            left join vendor ON vendor.vendorid = jb.vendorid
            left join products as p on jli.rawmaterialsid = p.product_id
            left join uom on uom.id =p.uom_id 
            left join customer_purchase cp on cp.customer_purchase_id=jb.customer_purchase_id
            where jb.deleted is not true and jb.compcode=:compcode and jli.deleted is not true 
            and {sql_condition} 1=1
            group by jb.joborderid,vendor.companyname ,vendor.contactname, cp.order_unique,cp.customer_purchase_id
            order by jb.created_on desc limit :limit offset :offset;
        """)

        results = query_to_dict(
            db_client.engine.execute(integrated_query,
                                     limit=results_per_page,
                                     offset=offset,
                                     vendorid=vendorid,
                                     joborderid=str(joborderid),
                                     joborderno=str(joborderno),
                                     type=str(type),
                                     status=str(status),
                                     compcode=compcode,
                                     customer_purchase_id=customer_purchase_id,
                                     product_id=product_id,
                                     start_date=start_date,
                                     end_date=end_date
                                     ))

        return {"total_results": results[0].get('total_count', None) if results else 0,
                "page": paged,
                "results_per_page": results_per_page,
                "results": results}


@job_order_api_route.route('/product_price/')
class ProductPrice(Resource):

    @login_required()
    @job_order_api_route.marshal_with(product_price_list_response)
    @job_order_api_route.doc(params=product_price_filter)
    def get(self):
        product_id = request.args.get('product_id', None)
        vendorid = request.args.get('vendorid', None)
        sql_con = ''

        if product_id:
            sql_con += ' and jli.rawmaterialsid =:product_id '

        if vendorid:
            sql_con += ' and j.vendorid =:vendorid '
        try:
            query = text(f'''
            select j.vendorid,
                   jli.rawmaterialsid as product_id,
                   coalesce(gli.rate_per_item, jli.rate_per_item::text) as rate_per_item,
                   coalesce(nullif(gli.gst, '')::integer, jli.gst) as gst,
                   jli.hsn,
                   coalesce(gli.created_on, jli.created_on)::date as created_on
            from joborder j
            join joline_items jli on jli.jo_id = j.joborderid
            left join grnlineitems gli on gli.purchase_items_id = jli.id
            where j.deleted is not true and jli.deleted is not true {sql_con}
            order by coalesce(gli.created_on, jli.created_on) desc
            limit 1
            ''')
            result = query_to_dict(db_client.engine.execute(query,
                                                            vendorid=vendorid,
                                                            product_id=product_id))

            return {
                'results': result
            }

        except Exception as e:
            return map_sqlalchemy_error_to_http_status(e)


@job_order_api_route.route('/amend_log/<joborder_id>/')
class JobOrderAmendLog(Resource):

    @login_required()
    @job_order_api_route.marshal_with(amendment_log_response)
    def get(self, joborder_id):
        try:
            query = text('''
                select *,
                 count(*) over() as total_count
                 from joborder_amend_log
                where joborderid = :joborder_id
                order by created_on desc
            ''')
            result = query_to_dict(db_client.engine.execute(query, joborder_id=joborder_id))
            return {
                'success': True,
                'results_per_page': result[0].get('total_count') if result else 0,
                'results': result
            }
        except Exception as e:
            return map_sqlalchemy_error_to_http_status(e)