from sqlalchemy import Column, VARCHAR, BigInteger, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy.dialects.postgresql import NUMERIC, BYTEA

from .. import db_client


class LineMap(db_client.Model, SerializerMixin):
    __tablename__ = 'line_map'

    line_map_id = Column(BigInteger, primary_key=True)
    line_process_id = Column(BigInteger)
    config_map_id = Column(BigInteger) ## from skill
    count = Column(NUMERIC)
    compcode = Column(BigInteger)
    created_on = Column(DateTime)
    created_by = Column(VARCHAR(255))
    modified_on = Column(DateTime)
    modified_by=Column(VARCHAR(100))
    deleted_at = Column(DateTime)
    deleted = Column(Boolean, default=False)


# db_client.create_all()




