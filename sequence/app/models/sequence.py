import datetime
from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean, Integer, String, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import NUMERIC
from sqlalchemy.orm import relationship
from sqlalchemy_json import NestedMutableJson
from sqlalchemy_serializer import SerializerMixin

from .. import db_client



class ProductSeq(db_client.Model, SerializerMixin):
    __tablename__ = 'product_group_seq'

    product_group_seq_id = Column(BigInteger, primary_key=True)
    product_group_id = Column(BigInteger)
    attribute_id = Column(BigInteger)
    isproduct = Column(Boolean, default=False)
    rank = Column(BigInteger)
    description = Column(VARCHAR(255))
    modified_on = Column(DateTime)
    created_on = Column(DateTime)
    created_by = Column(VARCHAR(255))
    modified_by = Column(VARCHAR(255))
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    compcode = Column(BigInteger)

db_client.create_all()


