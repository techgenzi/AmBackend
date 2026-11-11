import datetime
from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy_json import NestedMutableJson
from .. import db_client

class TenantConfiguration(db_client.Model, SerializerMixin):
    __tablename__ = 'custome_config'

    id = Column(BigInteger, primary_key=True)
    compcode = Column(BigInteger, nullable=False, index=True)
    module_name = Column(VARCHAR(50), nullable=False)
    config_type = Column(VARCHAR(50), nullable=False)
    config_data = Column(NestedMutableJson, nullable=False, default=dict)
    created_on = Column(DateTime, default=datetime.datetime.utcnow)
    created_by = Column(VARCHAR(100))
    deleted = Column(Boolean, default=False)
    deleted_by = Column(VARCHAR(100), nullable=True)
    deleted_at = Column(DateTime, nullable=True)

db_client.create_all()
