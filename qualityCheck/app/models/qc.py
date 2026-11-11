import datetime
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
    total_item = Column(BigInteger)
    total_price = Column(NUMERIC(10, 2))
    supplierId = Column(BigInteger)
    grndate = Column(DateTime)
    vendorid = Column(BigInteger)
    inviceno = Column(VARCHAR(20))
    invice_attach = Column(VARCHAR(250))
    deliverychallan_no = Column(VARCHAR(50))
    dc_attach = Column(VARCHAR(250))
    grn_reason = Column(VARCHAR(100))  # new fields
    status = Column(Text)
    grn_description = Column(VARCHAR(1000))
    return_date = Column(DateTime)
    vehicle_number = Column(VARCHAR(255))
    is_qc_done = Column(Boolean, default=False)
    driver_name = Column(VARCHAR(255))
    driver_number = Column(VARCHAR(255))
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
    reason = Column(JSON)
    remark = Column(Text)
    total_price = Column(NUMERIC(10, 2))
    received_quantity = Column(NUMERIC)
    damaged_quantity=Column(NUMERIC)
    image_attachment = Column(JSON)
    rate_per_item = Column(VARCHAR(50))
    purchase_items_id = Column(BigInteger)
    gst = Column(VARCHAR(50))
    uom=Column(VARCHAR(25))
    non_damaged_quantity = Column(VARCHAR(50))
    supplier_lot_no = Column(VARCHAR(100), nullable=True)
    is_qc_done = Column(Boolean, default=False)
    qc_status = Column(VARCHAR(50), default='PENDING')
    taxes=Column(NestedMutableJson)
    modified_by = Column(VARCHAR(100))
    modified_on = Column(DateTime)
    created_by = Column(VARCHAR(100))
    created_on = Column(DateTime)
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)

class Location(db_client.Model, SerializerMixin):
    __tablename__ = 'store_location'

    store_id = Column(BigInteger, primary_key = True)
    store_name = Column(VARCHAR(255))
    description = Column(Text)
    modified_by = Column(VARCHAR(100))
    modified_on = Column(DateTime)
    created_by = Column(VARCHAR(100))
    created_on = Column(DateTime)
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)

class QualityAttributesConfig(db_client.Model, SerializerMixin):
    __tablename__ = 'quality_attributes_config'

    id = Column(BigInteger, primary_key=True)
    compcode = Column(BigInteger, nullable=False, index=True)
    customer_id = Column(BigInteger, nullable=True)
    raw_material_id = Column(BigInteger, nullable=True)
    attribute_name = Column(VARCHAR(100), nullable=False)
    attribute_type = Column(VARCHAR(50), nullable=False, default='boolean')
    min_value = Column(NUMERIC, nullable=True)
    max_value = Column(NUMERIC, nullable=True)
    is_required = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class GrnQcMeasurements(db_client.Model, SerializerMixin):
    __tablename__ = 'grn_qc_measurements'

    id = Column(BigInteger, primary_key=True)
    grn_line_id = Column(BigInteger, nullable=False)
    spec_id = Column(BigInteger, ForeignKey('quality_attributes_config.id', ondelete='CASCADE'), nullable=False)
    measured_value = Column(VARCHAR(255))
    is_passed = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

db_client.create_all()
