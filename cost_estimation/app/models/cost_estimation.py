import datetime
from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean, Integer, String, ForeignKey, Numeric, Text, JSON
from sqlalchemy.dialects.postgresql import NUMERIC
from sqlalchemy_json import NestedMutableJson
from sqlalchemy_serializer import SerializerMixin

from .. import db_client

#email mobile in customer id
class Estimation(db_client.Model, SerializerMixin):
    __tablename__ = 'cost_estimation'
    cost_estimation_id = Column(BigInteger, primary_key=True)
    estimation_code = Column(VARCHAR(50))
    customer_id = Column(BigInteger)
    marketing_person = Column(VARCHAR(255))
    estimate_date = Column(DateTime)
    description = Column(Text)
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(DateTime())
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)


class EstimationProduct(db_client.Model, SerializerMixin):
    __tablename__ = 'estimation_product'

    estimation_product_id = Column(BigInteger, primary_key=True)
    cost_estimation_id = Column(BigInteger)
    product_id = Column(BigInteger)
    quantity = Column(NUMERIC)
    admin_cost = Column(NUMERIC) #
    margin_cost = Column(NUMERIC) #
    transport_cost_per_piece = Column(NUMERIC) #
    eto_cost = Column(NUMERIC) #
    miscellaneous_cost = Column(NUMERIC)
    material_cost = Column(NUMERIC) #
    labour_cost = Column(NUMERIC) #
    packing_material_cost = Column(NUMERIC) #
    cost_definition = Column(JSON) #
    final_cost = Column(NUMERIC)
    description = Column(Text)
    compcode = Column(BigInteger)
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    modified_by = Column(DateTime())
    deleted_at = Column(DateTime())
    deleted = Column(Boolean, default=False)


# db_client.drop_all()

db_client.create_all()