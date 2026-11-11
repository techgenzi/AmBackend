from sqlalchemy import Column, VARCHAR, BigInteger, DateTime, Boolean, Time
from sqlalchemy.orm import relationship
from sqlalchemy_serializer import SerializerMixin

from .. import db_client

class LineConfig(db_client.Model, SerializerMixin):
    """
        Line configuration
    """
    __tablename__ = 'line_config'

    line_config_id = Column(BigInteger, primary_key=True)
    line_name = Column(VARCHAR(255))
    line_name_temp = Column(VARCHAR(255))
    description = Column(VARCHAR(255))
    line_id = Column(VARCHAR(255))
    compcode = Column(BigInteger)
    created_on = Column(DateTime)
    created_by = Column(VARCHAR(255))
    modified_on = Column(DateTime)
    modified_by = Column(VARCHAR(100))
    deleted_at = Column(DateTime)
    deleted = Column(Boolean, default=False)
class HourConfig(db_client.Model, SerializerMixin):
    """
        Line configuration
    """
    __tablename__ = 'hour_config'

    record_id = Column(BigInteger, primary_key=True)
    time_value=Column(VARCHAR(50))
    hour_starts = Column(Time)
    hour_ends = Column(Time)
    description = Column(VARCHAR(255))
    compcode = Column(BigInteger)
    created_on = Column(DateTime)
    created_by = Column(VARCHAR(255))
    modified_on = Column(DateTime)
    modified_by = Column(VARCHAR(100))
    deleted_at = Column(DateTime)
    deleted = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

db_client.create_all()