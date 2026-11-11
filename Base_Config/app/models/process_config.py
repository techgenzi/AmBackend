import datetime
from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean, Integer, String, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import NUMERIC
from sqlalchemy.orm import relationship
from sqlalchemy_json import NestedMutableJson
from sqlalchemy_serializer import SerializerMixin

from .. import db_client


class ProcessConfig(db_client.Model,SerializerMixin):

    __tablename__ = 'process_config'

    process_id = Column(BigInteger, primary_key=True)
    process_name = Column(VARCHAR(250))
    description = Column(VARCHAR(250))
    process_temp = Column(VARCHAR(255))
    add_att = Column(VARCHAR(255))
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    created_by = Column(VARCHAR(255))
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(150))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)


# db_client.create_all()