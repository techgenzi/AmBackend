import datetime
from logging import error

from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, bindparam, NUMERIC, Integer, String, update
from sqlalchemy.exc import SQLAlchemyError

# from invregistry.app.api.invregistry import query
from .. import db_client


def update_purchase_order(oper='+'):
    quantity_delivered_calculations = f'''COALESCE(quantity_delivered, 0.0) {oper} COALESCE(:non_damaged_quantity, 0.0)'''

    # Returning the SQL query with correct syntax
    return text(f'''
        UPDATE joline_items 
        SET quantity_delivered = {quantity_delivered_calculations},
            status = (
                CASE 
                    WHEN quandity > {quantity_delivered_calculations} THEN 'Partial'
                    WHEN {quantity_delivered_calculations} = 0 THEN status
                    ELSE 'Completed'
                END
            )
        WHERE id = :purchase_items_id 
    ''').bindparams(
            non_damaged_quantity=bindparam('non_damaged_quantity', type_=NUMERIC),
            purchase_items_id=bindparam('purchase_items_id', type_=Integer),
            # action=bindparam('action',type_=String),
            # status=bindparam('status', type_=String)
        )

def update_po_status():
    return text('''
    update joborder 
    set 
    is_done = (
        case 
            when not exists
                (
                select 1 from joline_items as jli
                where jli.jo_id=:jo_id and
                jli.status != 'Completed'
                )
            then True
        End
    )
    where joborderid =:jo_id
    ''').bindparams(
        jo_id=bindparam('jo_id', type_=NUMERIC)
    )

def delete_func(model,condition,pkey=None,fkey=''):
    error=''
    try:
        with db_client.session.begin():
            stmt = (
                update(model)
                .where(condition)  # Filter by GRNotes_id
                .values(deleted=True, deleted_at=datetime.datetime.now())  # Set 'deleted' and 'deleted_at' values
                .returning(*model.__table__.c)  # Return all columns using the table's columns
            )
            result = db_client.session.execute(stmt)
            sql_con=''
            if pkey:
                sql_con='and grnotesid=:grnotesid '
            if fkey:
                sql_con='and grnlineid=:grnlineid '
            sql_query=text(f'''
            select * from joline_items 
            where deleted is not true {sql_con}
            ''')
            sql_query=query_to_dict(db_client.engine.execute(sql_query,grnotesid=pkey,grnlineid=fkey))

            db_client.engine.execute(update_purchase_order('-'),sql_query)
        # returned_rows = [dict(row) for row in result]
        # db_client.engine.execute(update_purchase_order('-'), returned_rows)
        # self.db.session.commit()
    except SQLAlchemyError as e:
        error = str(e)
        db_client.session.rollback()
        # db_client.session.flush()
    return {
        'success': False if error else True,
        'error': error,
    }
