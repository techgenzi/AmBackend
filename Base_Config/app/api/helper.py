import hashlib
import json
from pprint import pprint

from flask import request,abort
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text

from .. import db_client
from ..api.errorhandling import map_sqlalchemy_error_to_http_status, update_local
from ..models.SequenceGenerate import SeqGenerate
from ..models.products import Products


def hash_check(product_group_id, product_name, variant_value_ids=None, compcode=None , product_id=None):
    query3 = text('''
    select pg.group_name from product_group as pg where product_group_id =:product_group_id''')
    result3 = query_to_dict(db_client.engine.execute(query3, product_group_id=product_group_id))
    if not result3:
        return abort(400, 'Mismatch data')
    group_name = result3[0].get('group_name', None)
    result = {}
    if variant_value_ids:
        query = text('''
            select va.variant_attribute_name,vv.variant_value from variant_value as vv 
            left join variant_attribute as va on vv.variant_attribute_id = va.variant_attribute_id
            where vv.deleted is not true and vv.compcode =:compcode and vv.variant_value_id in :variant_value_ids
        ''')
        attribute = query_to_dict(db_client.engine.execute(query, variant_value_ids=variant_value_ids,compcode=compcode))
        result.update({
            item['variant_attribute_name']: item['variant_value']
            for item in attribute
        })
    result['product_name'] = product_name
    result['group_name'] = group_name
    result['compcode'] = compcode
    pprint(result)
    sorted_json = json.dumps(result, sort_keys=True)
    pprint(sorted_json)
    hash_value = hashlib.sha256(sorted_json.encode()).hexdigest()
    print(hash_value, "HJK")
    sql_con = ''
    if product_id:
        sql_con += 'and product_id !=:product_id'
    query2 = text(f'''
    select * from products where hash_value =:hash_value and deleted is not true and compcode=:compcode {sql_con} and 1=1
    ''')
    duplicate = query_to_dict(db_client.engine.execute(query2, hash_value=hash_value, compcode=compcode, product_id=product_id))
    if duplicate:
        return abort(409, 'Duplicate')

    return hash_value

def seq(product_group_id,value,productname,compcode=None, s=db_client.session):
    query = text('''
    select pgs.product_group_id, pgs.attribute_id, pgs.isproduct, pgs.rank from product_group_seq as pgs where compcode=:compcode
    and product_group_id=:product_group_id and deleted is not true
    ''')
    if not compcode:
        curr = request.args.get('current_user', {})
        compcode = curr.get('company_id')
    order = s.execute(query, {'compcode': compcode, 'product_group_id': product_group_id}).mappings().all()
    print(order)
    sorted_order = sorted(order, key=lambda x: x['rank'])
    print(value)
    value_dict = {item['attribute_id']: item['value'] for item in value}

    results = []
    for item in sorted_order:
        if item['isproduct']:
            result = productname
        else:
            result = value_dict.get(item['attribute_id'])
        if result:
            results.append(str(result).strip())

    val = ' '.join(results)
    return val

def compute_hash(product_data):
    """Generates SHA-256 hash for the given product data."""
    sorted_json = json.dumps(product_data, sort_keys=True)  # Ensure consistent order
    return hashlib.sha256(sorted_json.encode()).hexdigest()


def fetch_product_data(compcode, s, variant_value_id):

    query = text('''
        SELECT 
            p.product_id, 
            pg.group_name, 
            p.hash_value, 
            p.product_name, 
            p.compcode,
            COALESCE(jsonb_object_agg(va.variant_attribute_name, vv.variant_value), '{}') AS attributes
        FROM products AS p
        LEFT JOIN product_group AS pg ON p.product_group_id = pg.product_group_id 
        LEFT JOIN product_variant AS pv ON p.product_id = pv.product_id
        LEFT JOIN variant_value AS vv ON vv.variant_value_id = pv.variant_value_id
        LEFT JOIN variant_attribute AS va ON va.variant_attribute_id = vv.variant_attribute_id
        where pg.compcode=:compcode and p.compcode=:compcode and pv.deleted is not true
        and p.deleted is not true and va.deleted is not true and vv.deleted is not true
        	and EXISTS (
        SELECT 1 
        FROM product_variant pv_sub
        JOIN variant_value vv_sub ON vv_sub.variant_value_id = pv_sub.variant_value_id
        WHERE pv_sub.product_id = p.product_id
        AND vv_sub.variant_value_id =:variant_value_id
    )
        GROUP BY p.product_id, pg.group_name, p.product_name, p.compcode;
    ''')

    result = s.execute(query, {'compcode': compcode, 'variant_value_id': variant_value_id}).fetchall()

    hash_input_dict = {}  # Dictionary for generating new hash values
    existing_hash_dict = {}  # Dictionary to check previous hash values

    for row in result:
        attributes = row.attributes  # Convert JSONB to Python dictionary

        product_data = {
            "product_name": row.product_name,
            "group_name": row.group_name,
            "compcode": row.compcode,
            **attributes  # Merge attributes dynamically
        }
        pprint(product_data)
        # Store in dictionary for hash computation
        hash_input_dict[row.product_id] = product_data

        # Store existing hash values for comparison
        existing_hash_dict[row.product_id] = row.hash_value

    return hash_input_dict, existing_hash_dict


def check_all_hash(variant_value_id, compcode=None,s=db_client.session):
    if not compcode:
        compcode = request.args.get('current_user', {}).get('company_id')

    hash_input_dict, existing_hash_dict = fetch_product_data(compcode=compcode, s=s, variant_value_id=variant_value_id)

    # Products to update
    update_data = []
    try:
        for product_id, product in hash_input_dict.items():
            # Create a dictionary without the existing hash
            product_data = {
                "product_name": product["product_name"],
                "group_name": product["group_name"],
                "compcode": product["compcode"],
                **product
            }

            # Generate the new hash
            new_hash = compute_hash(product_data)

            # Check if the hash has changed
            # if product["hash_value"] != new_hash:
            if existing_hash_dict.get(product_id) != new_hash:
                print(f"Updating hash for product_id {product_id}")
                update_data.append({
                    "product_id": product_id,
                    "hash_value": new_hash
                })

        # Bulk update using SQLAlchemy's update mapping
        print(update_data)
        if update_data:
            s.bulk_update_mappings(mapper=Products, mappings=update_data)
            s.commit()
            print(f"Updated {len(update_data)} products successfully.")
        else:
            print("No updates needed. All product hashes are up-to-date.")

        return {
            "message": "update successfully" if update_data else "No update required"
        }

    except Exception as e:
        s.flush()
        s.rollback()
        return map_sqlalchemy_error_to_http_status(e)


def get_product_sequence(s=db_client.session):
    current_user = request.args.get('current_user', {})
    company_id = current_user.get('company_id')

    query = text('''
        select * from seqgenerate
        where product_group = 'product' and compcode =:compcode
    ''')

    result = query_to_dict(db_client.engine.execute(query,
                                                    compcode=str(company_id)))
    # print(result, "SEQUENCE RESULT")
    sequence_num = None
    try:
        if True if result else False:
            prefix = result[0].get('prefix')
            last_no = result[0].get('lastno')
            zeropading = result[0].get('zeropadding')
            next_no = int(last_no)+1
            formatnum = str(next_no).zfill(zeropading)
            sequence_num = f"{prefix}{formatnum}"

            update_data = {
                'lastno': next_no
            }
            condition = SeqGenerate.seqgenerateid == result[0].get('seqgenerateid')

            update_local(model=SeqGenerate, s=s,condition=condition,values=update_data, commit=False)
        else:
            query = text('''
                            select count(*) from products where compcode=:compcode
                            ''')
            result = query_to_dict(db_client.engine.execute(query, compcode=company_id))
            count = result[0].get('count', 0) if result else 0
            next_no = int(count) + 1
            formatnum = str(int(next_no)).zfill(6)
            sequence_num = f"SKU-{formatnum}"

    except Exception as e:
        s.rollback()
        return map_sqlalchemy_error_to_http_status(e)

    return sequence_num


def generate_product_code(product_id, s=db_client.session, compcode=None):
    product_query = text("""
        SELECT product_id, product_name, product_group_id
        FROM products
        WHERE product_id = :product_id
          AND deleted IS NOT TRUE
    """)
    product = s.execute(product_query, {'product_id': product_id}).mappings().all()
    print(product, "PRODUCT DETAILS")
    if not product:
        return False
    product = product[0]
    product_name = product["product_name"]
    product_group_id = product["product_group_id"]

    variant_query = text("""
        SELECT
            vv.variant_attribute_id AS attribute_id,
            vv.variant_value        AS value
        FROM product_variant pv
        JOIN variant_value vv
            ON vv.variant_value_id = pv.variant_value_id
        WHERE pv.product_id = :product_id
          AND pv.deleted IS NOT TRUE
          AND vv.deleted IS NOT TRUE
    """)

    values = s.execute(variant_query, {"product_id": product_id}).mappings().all()

    product_code = seq(
        product_group_id=product_group_id,
        productname=product_name,
        value=values,
        compcode=compcode,
        s=s
    )
    print(product_code, "PRODUCT CODE")
    return product_code.strip()


def check_product_code_associated_to_variant_value(variant_value_id, s=db_client.session, compcode=None):
    try:
        query = text('''
        select p.product_id,p.product_code from product_variant pv
         join products p on pv.product_id=p.product_id
         where pv.variant_value_id =:variant_value_id and pv.deleted is not true
        ''')
        result = s.execute(query, {'variant_value_id': variant_value_id}).mappings().all()
        update_data = []
        if result:
            print(result, "RESULT IN PRODUCT CODE")
            for item in result:
                item = dict(item)
                product_id = item.get('product_id')
                product_code = generate_product_code(product_id, s=s, compcode=compcode)
                if not product_code:
                    continue
                if item.get('product_code') == product_code:
                    continue
                item['product_code'] = product_code
                update_data.append(item)

            s.bulk_update_mappings(mapper=Products, mappings=update_data)
            s.commit()
            return True

    except Exception as e:
        s.rollback()
        print(e, "ERROR IN CHECKING PRODUCT CODE")
        return map_sqlalchemy_error_to_http_status(e)


def check_product_code_associated_to_product_group(product_group_id, s=db_client.session, compcode=None):
    try:
        query = text('''
        select p.product_id,p.product_code from products p
         where p.product_group_id =:product_group_id and p.deleted is not true
        ''')
        result = s.execute(query, {'product_group_id': product_group_id}).mappings().all()
        update_data = []
        if result:
            print(result, "RESULT IN PRODUCT CODE")
            for item in result:
                item = dict(item)
                product_id = item.get('product_id')
                product_code = generate_product_code(product_id, s=s, compcode=compcode)
                if not product_code:
                    continue
                if item.get('product_code') == product_code:
                    continue
                item['product_code'] = product_code
                update_data.append(item)

            s.bulk_update_mappings(mapper=Products, mappings=update_data)
            s.commit()
            return True

    except Exception as e:
        s.rollback()
        print(e, "ERROR IN CHECKING PRODUCT CODE")
        return map_sqlalchemy_error_to_http_status(e)