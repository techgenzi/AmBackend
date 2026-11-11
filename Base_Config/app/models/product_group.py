import datetime
from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean, Integer, String, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import NUMERIC
from sqlalchemy.orm import relationship
from sqlalchemy_json import NestedMutableJson
from sqlalchemy_serializer import SerializerMixin

from .. import db_client


class ProductGroup(db_client.Model,SerializerMixin):
    __tablename__ = 'product_group'
    product_group_id = Column(BigInteger, primary_key=True)
    group_name = Column(VARCHAR(250))
    description=Column(VARCHAR(250))
    add_att = Column(VARCHAR(255))
    compcode=Column(BigInteger)
    created_on = Column(DateTime())
    created_by = Column(VARCHAR(255))
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(150))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)

    attributes = relationship("ProductGroupAttribute", backref="product_group")

class ProductGroupAttribute(db_client.Model, SerializerMixin):
    __tablename__ = 'product_group_attribute'

    product_group_attribute_id = Column(BigInteger, primary_key=True)
    product_group_id = Column(BigInteger, ForeignKey('product_group.product_group_id'))
    attribute_id = Column(BigInteger, ForeignKey('variant_attribute.variant_attribute_id'))
    add_att = Column(VARCHAR(255))
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    created_by = Column(VARCHAR(255))
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(150))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)



# db_client.create_all()
        #variant_attribute
