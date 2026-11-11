
from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean, Integer, String, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import NUMERIC
from sqlalchemy_json import NestedMutableJson
from sqlalchemy_serializer import SerializerMixin

from .. import db_client


class PackingProcess(db_client.Model,SerializerMixin):
    __tablename__ = 'packing_plan'
    packing_process_id = Column(BigInteger, primary_key=True)
    package_unique=Column(VARCHAR(100))
    order_items_id=Column(BigInteger)
    packing_date =Column(DateTime)
    end_date=Column(DateTime)
    is_done=Column(Boolean,default=False)
    quantity=Column(NUMERIC)
    packed_quantity=Column(NUMERIC)
    compcode=Column(BigInteger)
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(150))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)

class PackingMaterials(db_client.Model,SerializerMixin):
    __tablename__ = 'packing_materials'
    meterials_id= Column(BigInteger, primary_key=True)
    packing_process_id = Column(BigInteger)
    product_id =Column(BigInteger)
    is_packing_materials=Column(Boolean,default=False)
    quantity=Column(NUMERIC)
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(150))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)


        #variant_attribute
