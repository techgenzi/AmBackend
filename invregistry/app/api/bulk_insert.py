from sqlalchemy import text, bindparam, Integer, NUMERIC, String
from .. import db_client

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