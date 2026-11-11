import uuid
from sqlalchemy import Column, VARCHAR, BigInteger, DateTime, Boolean, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy_serializer import SerializerMixin
from datetime import datetime

from .. import db_client

class PipelineStages(db_client.Model, SerializerMixin):
    __tablename__ = 'pipeline_stages'
    __table_args__ = (
        UniqueConstraint('compcode', 'key', name='uq_pipeline_stages_compcode_key'),
    )
    serialize_rules = ('-leads',)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    compcode = Column(BigInteger, nullable=False, default=1, index=True)
    name = Column(VARCHAR(100), nullable=False)
    key = Column(VARCHAR(100), nullable=False)
    sequence_order = Column(Integer, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)
    color_code = Column(VARCHAR(7), default='#6B7280', nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SalesLeadPipelines(db_client.Model, SerializerMixin):
    __tablename__ = 'sales_lead_pipelines'
    serialize_rules = ('-stage.leads', '-customer.leads')

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    compcode = Column(BigInteger, nullable=False, default=1, index=True)
    customer_type = Column(VARCHAR(20), nullable=False) # 'NEW' or 'EXISTING'
    customer_id = Column(BigInteger, ForeignKey('vendor.vendorid', ondelete='SET NULL'), nullable=True)
    new_customer_name = Column(VARCHAR(255), nullable=True)
    new_customer_contact = Column(VARCHAR(50), nullable=True)
    new_customer_email = Column(VARCHAR(255), nullable=True)
    new_customer_address = Column(VARCHAR, nullable=True)
    stage_id = Column(UUID(as_uuid=True), ForeignKey('pipeline_stages.id'), nullable=False)
    tally_invoice_number = Column(VARCHAR(100), nullable=True)
    delivery_method = Column(VARCHAR(50), nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    stage = db_client.relationship('PipelineStages', backref='leads')
    customer = db_client.relationship('Vendors', backref='leads')
