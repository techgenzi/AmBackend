from sqlalchemy import Column, VARCHAR, BigInteger, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy.dialects.postgresql import NUMERIC, BYTEA

from .. import db_client


class DispatchRegistry(db_client.Model, SerializerMixin):
    __tablename__ = 'return_material'

    return_material_id = Column(BigInteger, primary_key=True)
    prod_plan_id = Column(BigInteger)
    unique_id = Column(VARCHAR(255))
    product_id = Column(BigInteger)
    user_id = Column(BigInteger)
    store_id = Column(BigInteger)
    return_request_amount = Column(NUMERIC)
    return_amount = Column(NUMERIC)
    status = Column(VARCHAR(50))
    moved_date = Column(DateTime)
    description = Column(Text)
    remarks = Column(Text)
    lot_no = Column(VARCHAR(100), nullable=True)
    compcode = Column(BigInteger)
    created_on = Column(DateTime)
    created_by = Column(VARCHAR(255))
    modified_on = Column(DateTime)
    modified_by=Column(VARCHAR(100))
    deleted_at = Column(DateTime)
    deleted = Column(Boolean, default=False)
    is_rejected = Column(Boolean, default=False)
    rejection_action = Column(VARCHAR(50))
    rejection_store_id = Column(BigInteger)


# db_client.create_all()




