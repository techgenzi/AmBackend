from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean, ForeignKey, DATE, JSON, TEXT
from sqlalchemy.dialects.postgresql import NUMERIC
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy.orm import relationship
from sqlalchemy_json import NestedMutableJson
from .. import db_client


# Job order
class Joborder(db_client.Model, SerializerMixin):
    __tablename__ = 'joborder'

    joborderid = Column(BigInteger, primary_key=True)
    joborderproposalid = Column(BigInteger, nullable=True)
    joborderno = Column(VARCHAR(50))
    compcode = Column(BigInteger)
    style = Column(VARCHAR(50))
    rawmaterials_id = Column(BigInteger)
    ordercompletiondate = Column(DateTime)
    type = Column(VARCHAR(50))
    jo_status = Column(VARCHAR(50), default='pending')
    jo_date = Column(DateTime)
    jo_doc = Column(DateTime)  # date of complition
    jo_valid_date = Column(DateTime)
    purchase_orderno = Column(VARCHAR(50))
    jo_aql = Column(NUMERIC(asdecimal=False))
    description = Column(VARCHAR(1000))
    jo_reason = Column(VARCHAR(100))
    termsand_condition = Column(VARCHAR(1000))
    customer_details=Column(NestedMutableJson)
    vendor_details=Column(NestedMutableJson)
    vendorid = Column(BigInteger, nullable=False)
    companyname = Column(VARCHAR(100))
    contactname = Column(VARCHAR(100))
    emailid = Column(VARCHAR(100))
    mobileno = Column(VARCHAR(30))
    gst_type = Column(VARCHAR(100))  #----->> new
    notes = Column(VARCHAR(500))  # -----------------> New
    payment_time = Column(VARCHAR(100))  # -----------------> New
    with_in_day = Column(VARCHAR(50))  # -----------------> New
    ship_addline1 = Column(VARCHAR(250))
    ship_addline2 = Column(VARCHAR(250))
    ship_district = Column(VARCHAR(50))
    ship_pincode = Column(BigInteger)
    notes = Column(TEXT)
    description = Column(TEXT)
    ship_city = Column(VARCHAR(50))
    ship_state = Column(VARCHAR(50))
    ship_country = Column(VARCHAR(50))
    modified_by = Column(VARCHAR(100))
    modified_on = Column(DateTime)
    created_by = Column(VARCHAR(100))
    created_on = Column(DateTime)
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)

class JobOrderLineItems(db_client.Model,SerializerMixin):
    __tablename__='joline_items'
    id = Column(BigInteger, primary_key=True)
    jo_id=Column(BigInteger)
    sku_id=Column(VARCHAR(50))
    product_name=Column(VARCHAR(250))
    product_details=Column(NestedMutableJson)
    uom = Column(VARCHAR(50))
    productGroup=Column(VARCHAR(100))
    rawmaterialsid=Column(BigInteger) #product_id
    quandity = Column(BigInteger)
    quantity_delivered = Column(NUMERIC)
    type = Column(VARCHAR(50))
    rate_per_item = Column(BigInteger)
    cgst_sgst = Column(BigInteger)
    gst = Column(BigInteger)
    igst = Column(BigInteger)
    boq = Column(NUMERIC)
    total_price = Column(NUMERIC)
    status=Column(VARCHAR(50))
    notes=Column(TEXT)
    description=Column(TEXT)
    compcode = Column(BigInteger)
    modified_by = Column(VARCHAR(255))
    modified_on = Column(DateTime)
    created_on = Column(DateTime)
    created_by = Column(VARCHAR(255))
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)

db_client.create_all()

