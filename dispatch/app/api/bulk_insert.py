from sqlalchemy import text, bindparam, Integer, NUMERIC, String
from .. import db_client

def inventory_ops():
    update_query = text('''
        UPDATE products SET allocated_quantity =  CASE 
        WHEN :action='Inward' Then COALESCE(allocated_quantity,0)+ COALESCE(cast(:approved_amount as numeric),0)
        ELSE COALESCE(allocated_quantity,0)- COALESCE(cast(:approved_amount as numeric),0) END
        WHERE product_id=:product_id and COALESCE(:status,'Rejected')='Approved' and releseid=:releseid
    ''').bindparams(
            approved_amount=bindparam('approved_amount', type_=NUMERIC),
            product_id=bindparam('product_id', type_=Integer),
            action=bindparam('action',type_=String),
            status=bindparam('status', type_=String),
        releseid=bindparam('releseid', type=Integer)
        )
    return update_query
            # ,grn_update())

def bin_ops():
    update_query=text('''
    Update vtm_warehouse set sku_id=:product_id,quantity=  CASE 
        WHEN :action='Inward' Then COALESCE(quantity,0)+ COALESCE(:approved_amount,0)
        ELSE COALESCE(quantity,0)- COALESCE(:approved_amount,0) END
        WHERE id=:bin_id and COALESCE(:status,'Rejected')='Approved'
    ''').bindparams(
            approved_amount=bindparam('approved_amount', type_=NUMERIC),
        product_id=bindparam('product_id', type_=Integer),
            bin_id=bindparam('bin_id', type_=Integer),
            action=bindparam('action',type_=String),
            status=bindparam('status', type_=Integer)
        )
    return update_query
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