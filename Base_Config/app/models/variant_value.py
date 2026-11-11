import datetime
from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean, Integer, String, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import NUMERIC
from sqlalchemy_json import NestedMutableJson
from sqlalchemy_serializer import SerializerMixin

from .. import db_client


class VariantValue(db_client.Model,SerializerMixin):
    __tablename__ = 'variant_value'
    variant_value_id = Column(BigInteger, primary_key=True)
    variant_attribute_id=Column(BigInteger, ForeignKey('variant_attribute.variant_attribute_id'))
    description = Column(Text)
    variant_value = Column(VARCHAR(100))
    variant_value_temp = Column(VARCHAR(100))
    add_att = Column(VARCHAR(255))
    compcode=Column(BigInteger)
    created_on = Column(DateTime())
    created_by = Column(VARCHAR(255))
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(150))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)


# db_client.drop_all()
# db_client.create_all()
        #variant_attribute
