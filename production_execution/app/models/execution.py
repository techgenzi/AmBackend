import datetime
from xmlrpc.client import boolean

from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean, Integer, String, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import NUMERIC
from sqlalchemy_json import NestedMutableJson
from sqlalchemy_serializer import SerializerMixin

from .. import db_client


class ProdExecution(db_client.Model,SerializerMixin):
    __tablename__ = 'prod_execution'
    id = Column(BigInteger, primary_key=True)
    prod_plan_id = Column(BigInteger)
    product_id=Column(BigInteger)
    stage_id = Column(BigInteger)
    wastage=Column(NUMERIC)
    inward_qty=Column(NUMERIC)
    is_material_recieved=Column(Boolean,default=False)
    outward_qty=Column(NUMERIC)
    opertaion_date=Column(DateTime)
    description = Column(Text)
    status=Column(Text) #pending approved rejected
    supplier_lot_no = Column(VARCHAR(100), nullable=True)
    production_lot_no = Column(VARCHAR(100), nullable=True)
    additional = Column(NestedMutableJson)
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(DateTime())
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)
db_client.create_all()