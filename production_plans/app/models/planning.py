from sqlalchemy import Column, BINARY, VARCHAR, CHAR, DateTime, BigInteger, ForeignKey, Boolean, Integer, Text
from sqlalchemy.dialects.postgresql import BYTEA, NUMERIC
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy_json import NestedMutableJson

from .. import db_client
from sqlalchemy_serializer import SerializerMixin

class ProdPlans(db_client.Model, SerializerMixin):
    __tablename__ = 'production_plan'
    production_plan_id =Column(BigInteger,primary_key=True)
    product_id=Column(BigInteger)
    planed_quantity=Column(NUMERIC)
    floor_id=Column(BigInteger)
    wastage=Column(NUMERIC)
    wastage_per=Column(NUMERIC)
    end_date=Column(DateTime)
    plan_unique=Column(VARCHAR(25))
    plan_date=Column(DateTime)
    execution_start_date=Column(DateTime)
    execution_end_date=Column(DateTime)
    is_emergency_plan=Column(Boolean,default=False)
    is_multi_product=Column(Boolean,default=False)
    moved_quantity = Column(NUMERIC)
    moved_date = Column(DateTime)
    is_done=Column(Boolean,default=False)
    labour_cost_per_product=Column(NUMERIC)
    total_labour_cost=Column(NUMERIC)
    total_material_cost = Column(NUMERIC)
    status=Column(VARCHAR(25))
    additional = Column(NestedMutableJson)
    lot_number = Column(VARCHAR(100))
    compcode = Column(BigInteger, index=True)
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(DateTime())
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False, index=True)

class PlanDetails(db_client.Model,SerializerMixin):
    __tablename__ = 'plan_details'
    plan_details_id=Column(BigInteger, primary_key=True)
    production_plan_id=Column(BigInteger, index=True)
    plan_quantity=Column(NUMERIC)
    wastage=Column(NUMERIC)
    wastage_per=Column(NUMERIC)
    order_extract_id =Column(BigInteger)
    lot_number = Column(VARCHAR(100))
    cpo_item_lot_id = Column(BigInteger)
    is_done=Column(Boolean,default=False)
    compcode = Column(BigInteger, index=True)
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(DateTime())
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False, index=True)

class PlanTargets(db_client.Model,SerializerMixin):
    __tablename__ = 'plan_targets'
    plan_target_id=Column(BigInteger,primary_key=True)
    production_plan_id = Column(BigInteger, index=True)
    product_id=Column(BigInteger)
    target_quantity=Column(NUMERIC)
    stage_id=Column(BigInteger, index=True)
    process_id=Column(BigInteger)
    is_hourly_target=Column(Boolean)
    is_outsource=Column(Boolean,default=False)
    start_date=Column(DateTime)
    end_date=Column(DateTime)
    day_target=Column(NUMERIC)
    compcode = Column(BigInteger, index=True)
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(DateTime())
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False, index=True)
    alter_hours=Column(NUMERIC)



class InvRegistry(db_client.Model, SerializerMixin):
    __tablename__ = 'invregistry'

    releseid = Column(BigInteger, primary_key=True)
    product_id = Column(BigInteger)
    requested_amount = Column(NUMERIC)
    approved_amount = Column(NUMERIC)
    action = Column(Text)
    ref_id = Column(Text)
    prod_plan_id = Column(BigInteger)
    manual_count = Column(VARCHAR(255))
    packing_process_id = Column(BigInteger)
    invoice_id = Column(VARCHAR(50))
    is_returned = Column(Boolean)
    status = Column(Text)
    # manual_count = VARCHAR(255)
    approval_id = Column(BigInteger)
    approval_date = Column(DateTime)
    issued_date = Column(DateTime)
    userid = Column(BigInteger)
    is_from = Column(Text)
    description = Column(Text)
    doc_id = Column(VARCHAR(100))
    compcode = Column(BigInteger)
    created_on = Column(DateTime)
    created_by = Column(VARCHAR(255))
    modified_on = Column(DateTime)
    modified_by = Column(VARCHAR(100))
    deleted_at = Column(DateTime)
    deleted = Column(Boolean, default=False)
    grn_item_id = Column(BigInteger)
    type = Column(VARCHAR(50))
    is_dispatch = Column(Boolean)
    store_id = Column(BigInteger)

class Products(db_client.Model):
    __tablename__ = 'products'
    product_id = Column(BigInteger, primary_key=True)


class Style(db_client.Model, SerializerMixin):
    __tablename__ = 'style'

    style_id = Column(BigInteger, primary_key=True)
    style_code = Column(VARCHAR(255))
    allowed_wastage = Column(VARCHAR(50))
    description = Column(Text)
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    created_by = Column(VARCHAR(255))
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(150))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)


class StyleProduct(db_client.Model, SerializerMixin):
    __tablename__ = 'style_product'

    style_product_id = Column(BigInteger, primary_key=True)
    style_id = Column(BigInteger, ForeignKey('style.style_id'))
    product_id = Column(BigInteger, ForeignKey('products.product_id'))
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    created_by = Column(VARCHAR(255))
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(150))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)


class Category(db_client.Model, SerializerMixin):
    __tablename__ = 'category'

    category_id = Column(BigInteger, primary_key=True)
    category_name = Column(VARCHAR(255))
    # style_id = Column(BigInteger, ForeignKey('style.style_id'))
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    created_by = Column(VARCHAR(255))
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(150))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)


class StyleCategory(db_client.Model, SerializerMixin):
    __tablename__ = 'style_category'

    style_category_id = Column(BigInteger, primary_key=True)
    category_id = Column(BigInteger, ForeignKey('category.category_id'))
    style_id = Column(BigInteger, ForeignKey('style.style_id'))
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    created_by = Column(VARCHAR(255))
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(150))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)


class FGLog(db_client.Model, SerializerMixin):
    __tablename__ = 'fg_to_store_log'

    log_id = Column(BigInteger, primary_key=True)
    production_plan_id = Column(BigInteger)
    moved_quantity = Column(NUMERIC)
    cost_of_rawmaterial = Column(NUMERIC)
    store_id = Column(BigInteger)
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    created_by = Column(VARCHAR(255))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)


class FGLogDetails(db_client.Model, SerializerMixin):
    __tablename__ = 'fg_to_store_log_detail'

    detail_id = Column(BigInteger, primary_key=True)
    log_id = Column(BigInteger)
    product_id = Column(BigInteger)
    quantity = Column(NUMERIC)
    cost_per_product = Column(NUMERIC)
    total_cost = Column(NUMERIC)
    creted_on = Column(DateTime(timezone=True))
    created_by = Column(VARCHAR(255))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)


class ProductionMaterialCost(db_client.Model, SerializerMixin):
    __tablename__ = 'production_material_cost'

    production_material_cost_id = Column(BigInteger, primary_key=True)
    production_plan_id = Column(BigInteger)
    product_id = Column(BigInteger)
    dispatch_amount = Column(NUMERIC)
    return_amount = Column(NUMERIC)
    consumed = Column(NUMERIC)
    total_cost = Column(NUMERIC)
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    created_by = Column(VARCHAR(255))
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(150))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)

class ProductionPlanProducts(db_client.Model, SerializerMixin):
    __tablename__ = 'production_plan_products'
    id = Column(BigInteger, primary_key=True)
    production_plan_id = Column(BigInteger, index=True)
    product_id = Column(BigInteger, index=True)
    planned_quantity = Column(NUMERIC)
    moved_quantity = Column(NUMERIC, default=0)
    moved_date = Column(DateTime)
    wastage = Column(NUMERIC)
    wastage_per = Column(NUMERIC)
    floor_id = Column(BigInteger)
    compcode = Column(BigInteger, index=True)
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    deleted = Column(Boolean, default=False)

# db_client.create_all()


