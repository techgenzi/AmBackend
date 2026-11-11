import datetime
from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean, Integer, String, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import NUMERIC
from sqlalchemy_json import NestedMutableJson
from sqlalchemy_serializer import SerializerMixin

from .. import db_client


class ProdStages(db_client.Model,SerializerMixin):
    __tablename__ = 'production_stages'
    id = Column(BigInteger, primary_key=True)
    rank_id = Column(BigInteger)
    product_id = Column(BigInteger)
    stage_name = Column(Text)
    ref_id=Column(BigInteger)
    stage_id=Column(BigInteger)
    activity_config_id = Column(BigInteger)
    target_per_hour = Column(NUMERIC)
    required_quantity_per_unit = Column(NUMERIC)
    is_config=Column(Boolean,default=False)
    is_serialization = Column(Boolean, default=False)
    serialization_params = Column(NestedMutableJson)
    description = Column(Text)
    additional = Column(NestedMutableJson)
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(DateTime())
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)
class ActivityStageMap(db_client.Model,SerializerMixin):
    __tablename__ = 'activity_stage_map'
    activity_stage_map_id = Column(BigInteger, primary_key=True)
    config_id=Column(BigInteger)
    production_stage_id=Column(BigInteger)
    is_final_process=Column(Boolean, default=False)
    target_per_hour=Column(NUMERIC)
    compcode=Column(BigInteger)
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(150))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)


db_client.create_all()
