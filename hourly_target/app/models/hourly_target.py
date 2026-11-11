import datetime
from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean, Integer, String, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import NUMERIC
from sqlalchemy_json import NestedMutableJson
from sqlalchemy_serializer import SerializerMixin

from .. import db_client


class HourlyTarget(db_client.Model,SerializerMixin):
    __tablename__ = 'hourly_target'
    hourly_target_id = Column(BigInteger, primary_key=True)
    plan_id=Column(BigInteger, index=True)
    doc_id=Column(NUMERIC)
    hour_estimate_quantity=Column(NUMERIC)
    alter_hours=Column(VARCHAR(50))
    compcode=Column(BigInteger, index=True)
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(150))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False, index=True)

db_client.create_all()
        #variant_attribute
