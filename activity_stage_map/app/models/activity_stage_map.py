import datetime
from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean, Integer, String, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import NUMERIC
from sqlalchemy_json import NestedMutableJson
from sqlalchemy_serializer import SerializerMixin

from .. import db_client


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
# db_client.create_all()

        #variant_attribute

class ProcessIncentiveSlabs(db_client.Model,SerializerMixin):
    __tablename__ = 'process_incentive_slabs'
    id = Column(BigInteger, primary_key=True)
    activity_stage_map_id = Column(BigInteger, ForeignKey('activity_stage_map.activity_stage_map_id'))
    from_qty = Column(NUMERIC)
    to_qty = Column(NUMERIC)
    incentive_amount = Column(NUMERIC)
    compcode = Column(BigInteger)
    created_on = Column(DateTime(), default=datetime.datetime.now)
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(150))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)

db_client.create_all()
