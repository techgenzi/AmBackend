from sqlalchemy import Column, BigInteger, Integer, VARCHAR, TEXT, DateTime, Boolean
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy_serializer import SerializerMixin
from datetime import datetime
from .. import db_client

class WhatsAppTenantConfig(db_client.Model, SerializerMixin):
    __tablename__ = 'whatsapp_tenant_configs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, nullable=False)
    compcode = Column(VARCHAR(10), nullable=False)
    phone_number_id = Column(VARCHAR(50), unique=True, nullable=False)
    waba_id = Column(VARCHAR(50), nullable=False)
    system_user_access_token = Column(TEXT, nullable=False)
    display_phone_number = Column(VARCHAR(20))
    status = Column(VARCHAR(20), default='Active')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WhatsAppIncomingMessage(db_client.Model, SerializerMixin):
    __tablename__ = 'whatsapp_incoming_messages'
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_sid = Column(VARCHAR(100), unique=True, nullable=False)
    tenant_id = Column(Integer, nullable=False)
    compcode = Column(VARCHAR(10), nullable=False)
    sender_mobile = Column(VARCHAR(20), nullable=False)
    raw_text = Column(TEXT, nullable=False)
    message_type = Column(VARCHAR(20), default='Unknown')  # 'Chat' or 'Order'
    extracted_json = Column(JSON)  # Using mysql JSON or equivalent Dialect JSON
    status = Column(VARCHAR(20), default='Pending')  # 'Pending', 'Parsed', 'Failed', 'Ignored'
    created_at = Column(DateTime, default=datetime.utcnow)
