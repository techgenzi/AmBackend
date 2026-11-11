from sqlalchemy import Column, VARCHAR, BigInteger, DateTime, Boolean, ForeignKey, JSON, Text, Integer
from sqlalchemy.orm import relationship
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy.dialects.postgresql import NUMERIC, BYTEA

from .. import db_client


class Labour(db_client.Model, SerializerMixin):
    __tablename__ = 'labour_cost'

    labour_cost_id = Column(BigInteger, primary_key=True)
    product_id = Column(BigInteger)
    stage_count = Column(Integer)
    rate_per_piece = Column(NUMERIC)
    rate_per_box = Column(NUMERIC)
    add_attribute = Column(JSON)
    compcode = Column(BigInteger)
    modified_by = Column(VARCHAR(100))
    modified_on = Column(DateTime)
    created_by = Column(VARCHAR(100))
    created_on = Column(DateTime)
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)


class LabourLog(db_client.Model, SerializerMixin):
    __tablename__ = 'labour_cost_log'

    labour_cost_log_id = Column(BigInteger, primary_key=True)
    labour_cost_id = Column(BigInteger)
    product_id = Column(BigInteger)
    stage_count = Column(Integer)
    rate_per_piece = Column(NUMERIC)
    rate_per_box = Column(NUMERIC)
    add_attribute = Column(JSON)
    compcode = Column(BigInteger)
    created_by = Column(VARCHAR(100))
    created_on = Column(DateTime)
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)

# db_client.drop_all()
#
# db_client.create_all()

