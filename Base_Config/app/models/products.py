import datetime
from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean, Integer, String, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import NUMERIC
from sqlalchemy.orm import relationship
from sqlalchemy_json import NestedMutableJson
from sqlalchemy_serializer import SerializerMixin

from .. import db_client


class Products(db_client.Model, SerializerMixin):
    __tablename__ = 'products'
    product_id = Column(BigInteger, primary_key=True)
    product_group_id=Column(BigInteger, ForeignKey('product_group.product_group_id'))
    product_code = Column(VARCHAR(250))
    sku_id = Column(VARCHAR(255))
    product_name=Column(Text)
    description=Column(VARCHAR(250))
    type = Column(VARCHAR(255))
    is_configurable=Column(Boolean)
    is_active=Column(Boolean, default=False)
    hash_value = Column(Text)
    product_count = Column(NUMERIC)
    base_uom=Column(VARCHAR(50))
    roql = Column(NUMERIC)
    effective_date = Column(DateTime)
    cost = Column(Numeric)
    moving_avg_cost = Column(Numeric(15, 4), default=0.0)
    uom_id = Column(BigInteger)
    is_serializable = Column(Boolean, default=False)
    serialization_params = Column(NestedMutableJson)
    compcode=Column(BigInteger)
    created_on = Column(DateTime())
    created_by = Column(VARCHAR(255))
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(150))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)

    product_group = relationship('ProductGroup', backref='products')

class ProductsCostLog(db_client.Model, SerializerMixin):

    __tablename__ = 'cost_log'
    costlogid = Column(BigInteger, primary_key=True)
    product_id = Column(BigInteger)
    cost = Column(NUMERIC)
    effective_date = Column(DateTime)
    modified_by = Column(VARCHAR(255))

class ProductVariant(db_client.Model, SerializerMixin):
    __tablename__ = 'product_variant'
    product_variant_id = Column(BigInteger, primary_key=True)
    product_id = Column(BigInteger, ForeignKey('products.product_id'))
    variant_value_id = Column(BigInteger, ForeignKey('variant_value.variant_value_id'))
    sku = Column(VARCHAR(50))
    # variant_name = Column(Text)
    is_active = Column(Boolean, default=False)
    compcode = Column(BigInteger)
    lot_no = Column(VARCHAR(100), nullable=True)
    add_att = Column(VARCHAR(255))
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(VARCHAR(150))
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)


class LocationProduct(db_client.Model, SerializerMixin):
    __tablename__ = 'store_product'

    store_product_id = Column(BigInteger, primary_key = True)
    store_id = Column(BigInteger)
    product_id = Column(BigInteger)
    product_count = Column(NUMERIC)
    compcode = Column(BigInteger)
    lot_no = Column(VARCHAR(100), nullable=True)
    modified_by = Column(VARCHAR(100))
    modified_on = Column(DateTime)
    created_by = Column(VARCHAR(100))
    created_on = Column(DateTime)
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)

# db_client.create_all()
        #variant_attribute
