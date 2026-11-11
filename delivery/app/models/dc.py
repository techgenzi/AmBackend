from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean, ForeignKey, DATE, JSON, TEXT
from sqlalchemy_serializer import SerializerMixin
from .. import db_client


# Job order
class DeliveryModel(db_client.Model, SerializerMixin):
    __tablename__ = 'delivery'

    deliveryid = Column(BigInteger, primary_key=True)
    deliveryno = Column(VARCHAR(50))
    compcode = Column(BigInteger)
    customerid = Column(BigInteger)
    userid = Column(BigInteger)
    delivery_date = Column(DateTime)
    vendorid = Column(BigInteger)
    vehicle_number=Column(VARCHAR(25))
    driver_name=Column(VARCHAR(50))
    driver_number=Column(VARCHAR(25))
    status=Column(VARCHAR(25))
    is_drafted=Column(Boolean,default=False)
    description = Column(TEXT)
    termsand_condition = Column(TEXT)
    additional_attributes = Column(JSON)
    modified_by = Column(VARCHAR(100))
    modified_on = Column(DateTime)
    created_by = Column(VARCHAR(100))
    created_on = Column(DateTime)
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)

class DeliveryLineItems(db_client.Model,SerializerMixin):
    __tablename__='delivery_line_items'
    id =Column(BigInteger, primary_key=True)
    deliveryid=Column(BigInteger)
    workOrderLineId = Column(BigInteger)
    quantity = Column(BigInteger)
    # is_drafted=Column(Boolean,default=False)
    rejected_quantity = Column(BigInteger, default=0)
    is_rejected = Column(Boolean, default=False)
    rejection_action = Column(VARCHAR(50), nullable=True)
    rejection_store_id = Column(BigInteger, nullable=True)
    production_lot_no = Column(VARCHAR(100), nullable=True)
    compcode = Column(BigInteger)
    modified_by = Column(VARCHAR(255))
    modified_on = Column(DateTime)
    created_on = Column(DateTime)
    created_by = Column(VARCHAR(255))
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)

class DeliverySerializedItems(db_client.Model, SerializerMixin):
    __tablename__ = 'delivery_serialized_items'

    id = Column(BigInteger, primary_key=True)
    deliveryid = Column(BigInteger)
    delivery_line_item_id = Column(BigInteger)
    serial_number = Column(VARCHAR(255))
    compcode = Column(BigInteger)
    created_on = Column(DateTime)
    created_by = Column(VARCHAR(100))
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)

db_client.create_all()

