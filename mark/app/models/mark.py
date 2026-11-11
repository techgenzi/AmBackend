from sqlalchemy import Column, VARCHAR, BigInteger, DateTime, Boolean, ForeignKey, JSON, Text, Integer
from sqlalchemy.orm import relationship
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy.dialects.postgresql import NUMERIC, BYTEA

from .. import db_client


class Mark(db_client.Model, SerializerMixin):
    __tablename__ = 'mark'

    mark_id = Column(BigInteger, primary_key=True)
    product_id = Column(BigInteger)
    add_attribute = Column(JSON)
    compcode = Column(BigInteger)
    modified_by = Column(VARCHAR(100))
    modified_on = Column(DateTime)
    created_by = Column(VARCHAR(100))
    created_on = Column(DateTime)
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)


class MarkLine(db_client.Model, SerializerMixin):
    __tablename__ = 'mark_line'

    mark_line_id = Column(BigInteger, primary_key=True)
    mark_id = Column(BigInteger)
    product_id = Column(BigInteger)
    total_weight = Column(NUMERIC)
    add_attribute = Column(JSON)
    compcode = Column(BigInteger)
    created_by = Column(VARCHAR(100))
    created_on = Column(DateTime)
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)


class MarkLineLog(db_client.Model, SerializerMixin):
    __tablename__ = 'mark_line_log'

    mark_line_log_id = Column(BigInteger, primary_key=True)
    mark_line_id = Column(BigInteger)
    mark_id = Column(BigInteger)
    product_id = Column(BigInteger)
    total_weight = Column(NUMERIC)
    add_attribute = Column(JSON)
    compcode = Column(BigInteger)
    created_by = Column(VARCHAR(100))
    created_on = Column(DateTime)
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)


# db_client.drop_all()

# db_client.create_all()

