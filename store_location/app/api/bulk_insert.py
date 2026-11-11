from flask import request
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, bindparam, Integer, NUMERIC, String

from .errorhandling import update_local, map_sqlalchemy_error_to_http_status
from .. import db_client
from ..models.SequenceGenerate import SeqGenerate


def inventory_ops():
    update_query = text('''
        UPDATE products SET allocated_quantity=  CASE 
        WHEN :action='Outward' Then COALESCE(allocated_quantity::numeric,0)+ COALESCE(cast(:approved_amount as numeric),0)
        END
        WHERE product_id=:product_id and COALESCE(:status,'Rejected')='Approved'
    ''').bindparams(
            approved_amount=bindparam('approved_amount', type_=NUMERIC),
            product_id=bindparam('product_id', type_=Integer),
            action=bindparam('action',type_=String),
            status=bindparam('status', type_=String)
        )
    return update_query

def inventory_inv():
    update_query = text('''
        UPDATE products SET product_count=  CASE 
        WHEN :action='Inward' Then COALESCE(product_count::numeric,0)+ COALESCE(cast(:approved_amount as numeric),0)
        END
        WHERE product_id=:product_id and COALESCE(:status,'Rejected')='Approved'
    ''').bindparams(
        approved_amount=bindparam('approved_amount', type_=NUMERIC),
        product_id=bindparam('product_id', type_=Integer),
        action=bindparam('action', type_=String),
        status=bindparam('status', type_=String)
    )
    return update_query
        # ,grn_update())

    # try:
    #     db_client.engine.execute(update_query,data)
    # except:
    #     return abort(409,"There is Problem in relesing Stock")
def grn_update():
    update_query=text(f'''
    update rawmaterialtype set balance_amount=CASE 
        WHEN :action='Inward' Then COALESCE(balance_amount,0)+ COALESCE(:approved_amount,0)
        ELSE COALESCE(balance_amount,0)- COALESCE(:approved_amount,0) END
    where rawmetmast_id=:grn_item_id
    ''').bindparams(
            approved_amount=bindparam('approved_amount', type_=NUMERIC),
        grn_item_id=bindparam('grn_item_id',type_=Integer),
        action=bindparam('action',type_=String)
    )
    return update_query


def get_product_sequence(s=db_client.session):
    current_user = request.args.get('current_user', {})
    company_id = current_user.get('company_id')

    query = text('''
        select * from seqgenerate
        where product_group = 'store_transfer' and compcode =:compcode
    ''')

    result = query_to_dict(db_client.engine.execute(query,
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
            print(type(next_no), "Next No Type")

            update_data = {
                'lastno': next_no
            }
            condition = SeqGenerate.seqgenerateid == result[0].get('seqgenerateid')
            update_local(model=SeqGenerate, s=s, condition=condition, values=update_data, commit=False)
        else:
            query = text('''
                            select count(*) from store_products where compcode=:compcode
                            ''')
            result = query_to_dict(db_client.engine.execute(query, compcode=company_id))
            count = result[0].get('count', 0) if result else 0
            next_no = int(count) + 1
            formatnum = str(int(next_no)).zfill(6)
            sequence_num = f"REQ-{formatnum}"

    except Exception as e:
        s.rollback()
        return map_sqlalchemy_error_to_http_status(e)

    return sequence_num