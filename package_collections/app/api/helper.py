from sqlalchemy import text, BigInteger, bindparam, String


def data_extract(data=[]):
    return text('''
        WITH RECURSIVE cte AS (
        SELECT 
            pc.id,
            pc.pakage_id,
            pc.product_id,
            pc.needded_count,
            p.product_name,
            p.compcode,
            p.sku_id,
            p.product_code,
            p2.product_name AS pakage_name,
            pc.is_package_material,
            p2.sku_id AS pakage_sku,
            p2.product_code AS pakage_code
        FROM package_collections pc
        JOIN products AS p ON p.product_id = pc.product_id
        JOIN products AS p2 ON p2.product_id = pc.pakage_id
        where pc.pakage_id = :pakage_id and pc.deleted is not true
        UNION
    
        SELECT 
            cte.id,
            cte.pakage_id,
            pc.product_id,
            pc.needded_count*cte.needded_count as needded_count,
            p.product_name,
            p.compcode,
            p.sku_id,
            p.product_code,
            p2.product_name AS pakage_name,
            pc.is_package_material,
            p2.sku_id AS pakage_sku,
            p2.product_code AS pakage_code
        FROM cte
        JOIN package_collections pc ON pc.pakage_id = cte.product_id and pc.deleted is not true
        JOIN products AS p ON p.product_id = pc.product_id
        JOIN products AS p2 ON p2.product_id = pc.pakage_id
        WHERE pc.product_id != cte.product_id
    )
    
    SELECT 
        --id,
        pakage_id,
        product_id,
        needded_count,
        compcode,
        is_package_material
        --product_name,
        --sku_id,
        --product_code,
        --pakage_name,
        --pakage_sku,
        --pakage_code
    FROM cte
    WHERE product_id NOT IN (SELECT pakage_id FROM package_collections where deleted is not true)
    ''')
# .bindparams(
#     product_id=bindparam('product_id', type_=BigInteger),
#     needded_count=bindparam('needded_count', type_=String)
# ))