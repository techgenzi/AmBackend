from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean
from sqlalchemy_serializer import SerializerMixin

from .. import db_client


class UOM(db_client.Model, SerializerMixin):
    __tablename__ = 'uom'

    id = Column(BigInteger, primary_key=True)
    uom = Column(VARCHAR(255))
    description = Column(VARCHAR(250))
    is_config = Column(Boolean)
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    created_by = Column(VARCHAR(255))
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(250))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)
