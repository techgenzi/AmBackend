from xmlrpc.client import DateTime

from sqlalchemy import BigInteger, Column, DateTime, VARCHAR, Integer, Text, Boolean, ForeignKey
from sqlalchemy.dialects.mysql import NUMERIC
from sqlalchemy.orm import relationship
from sqlalchemy_json import NestedMutableJson
from sqlalchemy_serializer import SerializerMixin

primary_key = 'asset_map_id'
from .. import db_client

class CustomerOrder(db_client.Model,SerializerMixin):
    __tablename__='customer_purchase'
    customer_purchase_id=Column(BigInteger,primary_key=True)
    order_date =Column(DateTime)
    expected_receiving_date=Column(DateTime)
    order_unique=Column(VARCHAR(25))
    billing_address=Column(VARCHAR(250))
    shipping_address=Column(VARCHAR(250))
    customer_id=Column(Integer)
    customer_details=Column(NestedMutableJson)
    attachment=Column(Text)
    order_type=Column(VARCHAR(25))
    status=Column(VARCHAR(25)) # Approved ,Rejected ,Pending
    description=Column(Text)
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(DateTime())
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)
class CustomerOrderItems(db_client.Model,SerializerMixin):
    __tablename__='customer_purchase_items'
    items_id=Column(BigInteger,primary_key=True)
    customer_purchase_id=Column(ForeignKey('customer_purchase.customer_purchase_id'), nullable=False)
    product_id=Column(BigInteger)
    quantity_ordered=Column(NUMERIC)
    quantity_delivered=Column(NUMERIC)
    quantity_produced=Column(NUMERIC)
    product_attributes=Column(NestedMutableJson)
    delivery_product_code=Column(VARCHAR(25))
    description=Column(Text)
    status = Column(VARCHAR(25))  # Approved ,Rejected ,Pending
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(DateTime())
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)
    customer_purchase = relationship('CustomerOrder')

class OrderExtarct(db_client.Model,SerializerMixin):
    __tablename__ = 'order_items_extract'
    extract_id =Column(BigInteger,primary_key=True)
    order_items_id =Column(ForeignKey('customer_purchase_items.items_id'), nullable=False)
    product_id=Column(BigInteger)
    quantity_ordered=Column(BigInteger)
    quantity_planned=Column(NUMERIC)
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(DateTime())
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)
    customer_purchase = relationship('CustomerOrderItems')

class CPOItemLots(db_client.Model, SerializerMixin):
    __tablename__ = 'cpo_item_lots'
    id = Column(BigInteger, primary_key=True)
    customer_purchase_id = Column(BigInteger, nullable=False)
    cpo_item_id = Column(BigInteger, nullable=False)
    lot_number = Column(VARCHAR(100), nullable=False)
    lot_qty = Column(NUMERIC, nullable=False, default=0)
    compcode = Column(VARCHAR(50))
    deleted = Column(Boolean, default=False)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

from .whatsapp import WhatsAppTenantConfig, WhatsAppIncomingMessage
db_client.create_all()