from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import NUMERIC
from sqlalchemy_json import NestedMutableJson
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy.orm import relationship

from .. import db_client


# Goods Recive Notes
class GRNotes(db_client.Model, SerializerMixin):
    __tablename__ = 'grnotes'

    grnotesid = Column(BigInteger, primary_key=True)
    grn_no = Column(VARCHAR(50))
    grn_type = Column(VARCHAR(50))
    user_id = Column(BigInteger)
    compcode = Column(BigInteger)
    type = Column(VARCHAR(50))
    joborderid = Column(VARCHAR(50))
    bommaster_id = Column(BigInteger)
    is_moved = Column(Boolean, default=False)
    is_qc_done = Column(Boolean, default=False)
    total_item = Column(BigInteger)
    total_price = Column(NUMERIC(10, 2))
    supplierId = Column(BigInteger)
    grndate = Column(DateTime)
    status = Column(VARCHAR(255))
    vendorid = Column(BigInteger)
    inviceno = Column(VARCHAR(20))
    invice_attach = Column(VARCHAR(250))
    deliverychallan_no = Column(VARCHAR(50))
    dc_attach = Column(VARCHAR(250))
    grn_reason = Column(VARCHAR(100))  # new fields
    grn_description = Column(VARCHAR(1000))
    modified_by = Column(VARCHAR(100))
    modified_on = Column(DateTime)
    created_by = Column(VARCHAR(100))
    created_on = Column(DateTime)
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)

class GRNLineItems(db_client.Model, SerializerMixin):
    __tablename__ = 'grnlineitems'

    grnlineid = Column(BigInteger, primary_key=True)
    grnotesid = Column(BigInteger)
    product_id = Column(BigInteger)
    product_name = Column(Text)
    additional_attributes = Column(JSON)
    grn_type = Column(VARCHAR(50))
    user_id = Column(BigInteger)
    compcode = Column(BigInteger)
    is_moved = Column(Boolean, default=False)
    # total_item = Column(BigInteger)
    total_price = Column(NUMERIC(10, 2))
    reason = Column(Text)
    received_quantity = Column(NUMERIC)
    damaged_quantity=Column(NUMERIC)
    rate_per_item = Column(VARCHAR(50))
    purchase_items_id=Column(BigInteger)
    gst = Column(VARCHAR(50))
    uom=Column(VARCHAR(25))
    non_damaged_quantity = Column(VARCHAR(50))
    supplier_lot_no = Column(VARCHAR(100), nullable=True)
    taxes=Column(NestedMutableJson)
    modified_by = Column(VARCHAR(100))
    modified_on = Column(DateTime)
    created_by = Column(VARCHAR(100))
    created_on = Column(DateTime)
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)


db_client.create_all()
