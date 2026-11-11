import datetime
from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean, Integer, String, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import NUMERIC
from sqlalchemy_json import NestedMutableJson
from sqlalchemy_serializer import SerializerMixin

from .. import db_client


class Floor(db_client.Model, SerializerMixin):
    __tablename__ = 'floor'

    floor_id = Column(BigInteger, primary_key=True)
    floor_name = Column(VARCHAR(255))
    description = Column(VARCHAR(250))
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    created_by = Column(VARCHAR(255))
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(250))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)



    #variant_attribute
