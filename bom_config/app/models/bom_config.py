import datetime
from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean, ARRAY, Integer
from sqlalchemy_serializer import SerializerMixin

from .. import db_client


class BomConfig(db_client.Model, SerializerMixin):
    __table__name = 'bom_config'
    bom_config_id = Column(BigInteger, primary_key=True)
    maper_id = Column(ARRAY(Integer))
    mapping_id = Column(ARRAY(Integer))
    child_id = Column(ARRAY(Integer))
    map_type=Column(VARCHAR(50))
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(DateTime())
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)


# db_client.create_all()
# db_client.drop_all()