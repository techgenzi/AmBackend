from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean
from sqlalchemy_serializer import SerializerMixin

from .. import db_client


class Category(db_client.Model, SerializerMixin):
    __tablename__ = 'category'

    category_id = Column(BigInteger, primary_key=True)
    category_name = Column(VARCHAR(255))
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    created_by = Column(VARCHAR(255))
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(250))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)


class StyleCategory(db_client.Model, SerializerMixin):
    __tablename__ = 'style_category'

    style_category_id = Column(BigInteger, primary_key=True)
    style_id = Column(BigInteger)
    category_id = Column(BigInteger)
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    created_by = Column(VARCHAR(255))
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(250))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)
