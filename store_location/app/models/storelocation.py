from sqlalchemy import Column, VARCHAR, BigInteger, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy.dialects.postgresql import NUMERIC, BYTEA

from .. import db_client

# class InvRegistry(db_client.Model, SerializerMixin):
#     __tablename__ = 'invregistry'
#
#     releseid=Column(BigInteger,primary_key=True)
#     product_id=Column(BigInteger)
#     requested_amount=Column(NUMERIC)
#     approved_amount=Column(NUMERIC)
#     action=Column(Text)
#     ref_id=Column(Text)
#     prod_plan_id=Column(BigInteger)
#     manual_count=Column(VARCHAR(255))
#     packing_process_id = Column(BigInteger)
#     invoice_id=Column(VARCHAR(50))
#     is_returned =Column(Boolean)
#     status = Column(Text)
#     # manual_count = VARCHAR(255)
#     approval_id = Column(BigInteger)
#     approval_date = Column(DateTime)
#     issued_date=Column(DateTime)
#     userid = Column(BigInteger)
#     is_from=Column(Text)
#     description = Column(Text)
#     doc_id=Column(VARCHAR(100))
#     compcode = Column(BigInteger)
#     created_on = Column(DateTime)
#     modified_on = Column(DateTime)
#     modified_by=Column(VARCHAR(100))
#     deleted_at = Column(DateTime)
#     deleted = Column(Boolean, default=False)
#     grn_item_id=Column(BigInteger)
#     type = Column(VARCHAR(50))
#     is_dispatch = Column(Boolean)


class Location(db_client.Model, SerializerMixin):
    __tablename__ = 'store_location'

    store_id = Column(BigInteger, primary_key = True)
    store_name = Column(VARCHAR(255))
    location = Column(VARCHAR(255))
    description = Column(Text)
    compcode = Column(BigInteger)
    modified_by = Column(VARCHAR(100))
    modified_on = Column(DateTime)
    created_by = Column(VARCHAR(100))
    created_on = Column(DateTime)
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)

#
class LocationProduct(db_client.Model, SerializerMixin):
    __tablename__ = 'store_product'

    store_product_id = Column(BigInteger, primary_key = True)
    store_id = Column(BigInteger)
    product_id = Column(BigInteger)
    product_count = Column(NUMERIC)
    sub_location = Column(VARCHAR(255), nullable=True)
    lot_no = Column(VARCHAR(100), nullable=True)
    compcode = Column(BigInteger)
    modified_by = Column(VARCHAR(100))
    modified_on = Column(DateTime)
    created_by = Column(VARCHAR(100))
    created_on = Column(DateTime)
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)


class StoreTransfer(db_client.Model, SerializerMixin):
    __tablename__ = 'store_transfer'

    store_transfer_id = Column(BigInteger, primary_key=True)
    from_store_id = Column(BigInteger)
    to_store_id = Column(BigInteger)
    transfer_date = Column(DateTime)
    notes = Column(Text)
    status = Column(VARCHAR(50))
    release_status = Column(VARCHAR(50))
    receive_status = Column(VARCHAR(50))
    request_id = Column(VARCHAR(100))
    # product_id = Column(BigInteger)
    # quantity = Column(NUMERIC)
    compcode = Column(BigInteger)
    created_by = Column(VARCHAR(100))
    created_on = Column(DateTime)
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)


class StoreTransferItems(db_client.Model, SerializerMixin):
    __tablename__ = 'store_transfer_items'

    store_transfer_item_id = Column(BigInteger, primary_key=True)
    store_transfer_id = Column(BigInteger, ForeignKey('store_transfer.store_transfer_id'))
    # already_dispatch = Column(NUMERIC)
    # already_receive = Column(NUMERIC)
    product_id = Column(BigInteger)
    quantity = Column(NUMERIC)
    approved_qty = Column(NUMERIC)
    compcode = Column(BigInteger)
    created_by = Column(VARCHAR(100))
    created_on = Column(DateTime)
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)


class StoreRoleMap(db_client.Model, SerializerMixin):
    __tablename__ = 'store_role_map'

    store_role_map_id = Column(BigInteger, primary_key=True)
    store_id = Column(BigInteger)
    role_id = Column(BigInteger)
    compcode = Column(BigInteger)
    created_by = Column(VARCHAR(100))
    created_on = Column(DateTime)
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)


# db_client.drop_all()

db_client.create_all()

