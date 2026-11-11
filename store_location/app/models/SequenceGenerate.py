
from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean, Integer, String, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import NUMERIC
from sqlalchemy.orm import relationship
from sqlalchemy_serializer import SerializerMixin

from .. import db_client


class SeqGenerate(db_client.Model,SerializerMixin):
    __tablename__ = 'seqgenerate'
    seqgenerateid = Column(BigInteger, primary_key=True)
    customer_id = Column(BigInteger)
    description = Column(VARCHAR(255))
    prefix = Column(VARCHAR(50))
    lastno = Column(BigInteger)
    zeropadding = Column(BigInteger)
    customer_name = Column(VARCHAR(255))
    product_group = Column(VARCHAR(100))
    compcode=Column(VARCHAR(100))
    created_on = Column(DateTime())
    created_by = Column(VARCHAR(255))
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(150))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)