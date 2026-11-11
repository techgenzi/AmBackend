import datetime
from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean, Integer, String, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import NUMERIC
from sqlalchemy_json import NestedMutableJson
from sqlalchemy_serializer import SerializerMixin

from .. import db_client


class Stage(db_client.Model, SerializerMixin):
    __tablename__ = 'stage'

    stage_id = Column(BigInteger, primary_key=True)
    stage_name = Column(VARCHAR(255))
    description = Column(VARCHAR(250))
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    created_by = Column(VARCHAR(255))
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(250))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)
    is_serialization = Column(Boolean, default=False)
    serialization_params = Column(NestedMutableJson)
class Params(db_client.Model,SerializerMixin):
    __tablename__ = 'config_params'
    parameter_id=Column(BigInteger, primary_key=True)
    parameter_name=Column(VARCHAR(250))
    parameter_type=Column(VARCHAR(250))
    description = Column(Text)
    additional = Column(NestedMutableJson)
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(250))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)

class StageParams(db_client.Model,SerializerMixin):
    __tablename__ = 'stage_params'
    stage_param_id=Column(BigInteger, primary_key=True)
    stage_id = Column(BigInteger)
    parameter_id = Column(BigInteger)
    stage_param_value=Column(VARCHAR(250))
    is_eval=Column(Boolean, default=False)
    description = Column(Text)
    additional = Column(NestedMutableJson)
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(250))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)

db_client.create_all()