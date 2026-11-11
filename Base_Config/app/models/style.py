from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean
from sqlalchemy_serializer import SerializerMixin

from .. import db_client


class Style(db_client.Model, SerializerMixin):
    __tablename__ = 'style'

    style_id = Column(BigInteger, primary_key=True)
    style_code = Column(VARCHAR(255))
    description = Column(VARCHAR(250))
    allowed_wastage = Column(VARCHAR(50))
    attribute_id = Column(BigInteger)
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    created_by = Column(VARCHAR(255))
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(250))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)


class StyleProduct(db_client.Model, SerializerMixin):
    __tablename__ = 'style_product'

    style_product_id = Column(BigInteger, primary_key=True)
    style_id = Column(BigInteger)
    product_id = Column(BigInteger)
    attribute_id = Column(BigInteger)
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    created_by = Column(VARCHAR(255))
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(250))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)
