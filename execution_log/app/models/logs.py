import datetime

from flask_restx import Resource
from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean, Integer, String, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import NUMERIC
from sqlalchemy_json import NestedMutableJson
from sqlalchemy_serializer import SerializerMixin

from .. import db_client


class ExecutionLog(db_client.Model,SerializerMixin):
    __table__name = 'execution_log'
    id = Column(BigInteger, primary_key=True)
    target_id = Column(BigInteger)
    product_id = Column(BigInteger)
    stage_id = Column(BigInteger)
    process_id =Column(BigInteger)
    hour_config_id=Column(BigInteger)
    wastage = Column(NUMERIC)
    emp_id=Column(NUMERIC)
    labour_cost = Column(NUMERIC)
    line_id = Column(BigInteger)
    machine_id=Column(BigInteger)
    activity_id=Column(BigInteger)
    inward_qty = Column(NUMERIC)
    outward_qty = Column(NUMERIC)
    opertaion_start_date = Column(DateTime)
    opertaion_end_date = Column(DateTime)
    description = Column(Text)
    is_outsource =Column(Boolean)
    additional = Column(NestedMutableJson)
    serialized_units = Column(NestedMutableJson)
    supplier_lot_no = Column(VARCHAR(100), nullable=True)
    production_lot_no = Column(VARCHAR(100), nullable=True)
    job_order_id = Column(BigInteger, nullable=True)
    vendor_id = Column(BigInteger, nullable=True)
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(DateTime())
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)
class ExecutionCaptures(db_client.Model,SerializerMixin):
    __table__name = 'execution_captures'
    capture_id = Column(BigInteger, primary_key=True)
    stage_id = Column(BigInteger)
    rawmaterials_id=Column(BigInteger)
    parameter_id = Column(BigInteger)
    prod_plan_id=Column(BigInteger)
    operation_date=Column(DateTime)
    stage_param_value = Column(VARCHAR(250))
    is_eval = Column(Boolean, default=False)
    description = Column(Text)
    additional = Column(NestedMutableJson)
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(250))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)
class ExecutionRawmaterials(db_client.Model,SerializerMixin):
    __table__name = 'execution_rawmaterials'
    record_id=Column(BigInteger, primary_key=True)
    execution_id=Column(BigInteger)
    parameter_id = Column(BigInteger)
    operation_date = Column(DateTime)
    stage_param_value = Column(VARCHAR(250))
    rawmaterials_id = Column(BigInteger)
    is_eval = Column(Boolean, default=False)
    description = Column(Text)
    additional = Column(NestedMutableJson)
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(250))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)
    supplier_lot_no = Column(VARCHAR(100), nullable=True)
    production_lot_no = Column(VARCHAR(100), nullable=True)
    job_order_id = Column(BigInteger, nullable=True)
    vendor_id = Column(BigInteger, nullable=True)

# Deprecated: ItemSerialRegistry has been replaced by store_serialized_products.

# db_client.create_all()

