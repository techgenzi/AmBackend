from sqlalchemy import Column, VARCHAR, BigInteger, DateTime, Boolean, DATE, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy_json import NestedMutableJson
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy.dialects.postgresql import NUMERIC, BYTEA

from .. import db_client


class Vendors(db_client.Model, SerializerMixin):
    __tablename__ = 'vendor'

    vendorid = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger)
    compcode = Column(BigInteger)
    type = Column(VARCHAR(50))
    companyname = Column(VARCHAR(100))
    contactname = Column(VARCHAR(100))
    asset_attributes = Column(NestedMutableJson)
    emailid = Column(VARCHAR(100))
    mobileno = Column(VARCHAR(30))
    gstno = Column(VARCHAR(25))
    panno = Column(VARCHAR(15))
    bill_addline1 = Column(VARCHAR(250))
    bill_addline2 = Column(VARCHAR(250))
    bill_district = Column(VARCHAR(50))
    bill_pincode = Column(BigInteger)
    bill_city = Column(VARCHAR(50))
    bill_state = Column(VARCHAR(50))
    bill_country = Column(VARCHAR(50))
    same_as_add = Column(Boolean, default=False)
    ship_addline1 = Column(VARCHAR(250))
    ship_addline2 = Column(VARCHAR(250))
    ship_district = Column(VARCHAR(50))
    ship_pincode = Column(BigInteger)
    ship_city = Column(VARCHAR(50))
    ship_state = Column(VARCHAR(50))
    ship_country = Column(VARCHAR(50))
    discount_price = Column(VARCHAR(50))
    discount_percentage = Column(VARCHAR(50))
    credit_limit = Column(BigInteger)
    modified_by = Column(VARCHAR(100))
    modified_on = Column(DateTime)
    created_by = Column(VARCHAR(100))
    created_on = Column(DateTime)
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)


db_client.create_all()