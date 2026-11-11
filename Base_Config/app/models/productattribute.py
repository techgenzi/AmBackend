import datetime
from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean, Integer, String, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import NUMERIC
from sqlalchemy_json import NestedMutableJson
from sqlalchemy_serializer import SerializerMixin

from .. import db_client


class ProductAttribute(db_client.Model, SerializerMixin):
    __tablename__ = 'product_attribute'
    product_attribute_id = Column(BigInteger, primary_key=True)
    product_id=Column(BigInteger)
    attribute_meta_data_id=Column(BigInteger)
    product_attribute_value=Column(Text)
    compcode=Column(BigInteger)
    created_by = Column(VARCHAR(255))
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(150))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)

        #variant_attribute
