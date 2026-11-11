import datetime
from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean, Integer, String, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import NUMERIC
from sqlalchemy_json import NestedMutableJson
from sqlalchemy_serializer import SerializerMixin

from .. import db_client


class ProductGroupAttributesGroup(db_client.Model, SerializerMixin):
    __tablename__ = 'product_group_attributes_group'
    product_group_attributes_group_id = Column(BigInteger, primary_key=True)
    product_group_id=Column(BigInteger)
    attribute_group_id=Column(BigInteger)
    is_required=Column(Boolean,default=False)
    display_order=Column(Integer)
    compcode=Column(BigInteger)
    created_on = Column(DateTime())
    created_by = Column(VARCHAR(255))
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(150))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)

        #variant_attribute
