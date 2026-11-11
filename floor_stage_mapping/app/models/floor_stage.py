import datetime
from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean, ARRAY, Integer
from sqlalchemy_serializer import SerializerMixin

from .. import db_client


class FloorStageMap(db_client.Model, SerializerMixin):
    __tablename__ = 'floor_stage_map'

    floor_stage_id = Column(BigInteger, primary_key=True)
    floor_id = Column(BigInteger)
    stage_id = Column(BigInteger)
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(DateTime())
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)

db_client.create_all()
# db_client.drop_all()