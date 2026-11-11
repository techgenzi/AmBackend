import datetime
from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean, Integer, String, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import NUMERIC
from sqlalchemy_json import NestedMutableJson
from sqlalchemy_serializer import SerializerMixin

from .. import db_client

class Jo_po_Orders(db_client.Model, SerializerMixin):
    __tablename__ = 'jo_po_orders'
    id = Column(BigInteger, primary_key=True)
    doc_type=Column(VARCHAR(50)) #dc or f=jo
    po_id=Column(BigInteger)
    po_no=Column(VARCHAR(50))
    # product_details=Column(NestedMutableJson)
    # work_order=Column(NestedMutableJson)
    vendor_data=Column(NestedMutableJson)
    customer_data=Column(NestedMutableJson)
    vehicle_data=Column(NestedMutableJson)
    customer_id=Column(BigInteger)
    vendor_id=Column(BigInteger)
    order_date=Column(DateTime)
    board_at=Column(Text)
    gross_wt=Column(NUMERIC)
    net_wt=Column(NUMERIC)
    charges=Column(NestedMutableJson)
    no_qty=Column(NUMERIC)
    total_amount=Column(NUMERIC)
    total_no_items=Column(NUMERIC)
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(DateTime())
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)
db_client.create_all()