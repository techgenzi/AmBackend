import datetime
from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean, Integer, String, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import NUMERIC
from sqlalchemy.orm import relationship
from sqlalchemy_json import NestedMutableJson
from sqlalchemy_serializer import SerializerMixin

from .. import db_client

class VariantAttribute(db_client.Model,SerializerMixin):
    __tablename__ = 'variant_attribute'
    variant_attribute_id = Column(BigInteger, primary_key=True)
    variant_attribute_name = Column(VARCHAR(250))
    description = Column(VARCHAR(250))
    # data_type = Column(VARCHAR(250))
    # validation_rules = Column(Text)
    add_att = Column(VARCHAR(255))
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    created_by = Column(VARCHAR(255))
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(150))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)

    variant_attribute = relationship('ProductGroupAttribute', backref='variant_attribute')
    variant_value = relationship('VariantValue', backref='variant_attribute')


# db_client.create_all()