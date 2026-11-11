import datetime
from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean, Integer, String, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import NUMERIC
from sqlalchemy_json import NestedMutableJson
from sqlalchemy_serializer import SerializerMixin

from .. import db_client

class JoPoLineItems(db_client.Model, SerializerMixin):
    __tablename__ = 'jo_po_orders_items'
    id = Column(BigInteger, primary_key=True)
    order_id=Column(BigInteger)
    doc_id = Column(VARCHAR(50))
    # po_id = Column(BigInteger)
    # po_no = Column(VARCHAR(50))
    product_details = Column(NestedMutableJson)
    work_order = Column(NestedMutableJson)
    product_id = Column(BigInteger)
    hsn = Column(VARCHAR)
    no_items = Column(NUMERIC)  # bale
    qty = Column(NUMERIC)  #available_quantity=200 -->150 =50
    uom = Column(VARCHAR)
    rate_per_item = Column(NUMERIC)
    net_qty = Column(NUMERIC)
    amount_total = Column(NUMERIC)
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(DateTime())
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)
db_client.create_all()