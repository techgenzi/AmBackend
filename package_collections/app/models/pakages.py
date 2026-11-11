import datetime
from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean, Integer, String, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import NUMERIC
from sqlalchemy_serializer import SerializerMixin

from .. import db_client

class PakageCollections(db_client.Model, SerializerMixin):
    __tablename__ = 'package_collections'

    id = Column(BigInteger, primary_key=True)
    pakage_id = Column(BigInteger)
    product_id = Column(BigInteger)
    needded_count = Column(Numeric)
    is_package_material=Column(Boolean,default=False)
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(DateTime())
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)
class PakageItems(db_client.Model, SerializerMixin):
    __tablename__ = 'package_items'

    id = Column(BigInteger, primary_key=True)
    pakage_id = Column(BigInteger)
    product_id = Column(BigInteger)
    needded_count = Column(Numeric)
    is_package_material=Column(Boolean,default=False)
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(DateTime())
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)

db_client.create_all()