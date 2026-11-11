import datetime
from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean, Integer, String, ForeignKey, Text
from sqlalchemy.dialects.postgresql import NUMERIC
from sqlalchemy_serializer import SerializerMixin

from .. import db_client

class BOM(db_client.Model, SerializerMixin):
    __tablename__ = 'bom'
    bom_id = Column(BigInteger, primary_key=True)
    product_id = Column(BigInteger)
    uom = Column(String(50))
    description = Column(Text)
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(DateTime())
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)


class BOMComponent(db_client.Model, SerializerMixin):
    __tablename__ = 'bom_component'
    bom_component_id = Column(BigInteger, primary_key=True)
    bom_id = Column(BigInteger, ForeignKey('bom.bom_id'), nullable=False)
    product_id = Column(BigInteger)
    stage_id = Column(BigInteger)
    quantity = Column(VARCHAR(255))
    uom = Column(String(50))
    notes=Column(Text)
    is_optional = Column(Boolean)
    compcode = Column(BigInteger)
    is_mark_data = Column(Boolean, default=False)
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(DateTime())
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)


# db_client.create_all()