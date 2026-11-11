from sqlalchemy import Column, VARCHAR, BigInteger, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy.dialects.postgresql import NUMERIC, BYTEA

from .. import db_client

class DispatchRegistry(db_client.Model, SerializerMixin):
    __tablename__ = 'dispatch'

    dispatch_id = Column(BigInteger, primary_key=True)
    releseid=Column(BigInteger)
    user_id = Column(BigInteger)
    action = Column(Text)
    dispatch_amount = Column(NUMERIC)  #Quantity dispatched
    dispatch_cost = Column(NUMERIC)  #Cost of dispatched quantity
    store_id = Column(BigInteger)
    compcode = Column(BigInteger)
    created_on = Column(DateTime)
    created_by = Column(VARCHAR(255))
    modified_on = Column(DateTime)
    modified_by=Column(VARCHAR(100))
    deleted_at = Column(DateTime)
    deleted = Column(Boolean, default=False)
    lot_no = Column(VARCHAR(100), nullable=True)


class LocationProduct(db_client.Model, SerializerMixin):
    __tablename__ = 'store_product'

    store_product_id = Column(BigInteger, primary_key = True)
    store_id = Column(BigInteger)
    product_id = Column(BigInteger)
    product_count = Column(NUMERIC)
    lot_no = Column(VARCHAR(100), nullable=True)
    compcode = Column(BigInteger)
    modified_by = Column(VARCHAR(100))
    modified_on = Column(DateTime)
    created_by = Column(VARCHAR(100))
    created_on = Column(DateTime)
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)


db_client.create_all()



