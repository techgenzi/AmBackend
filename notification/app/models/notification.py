import datetime
from sqlalchemy import (Column, BigInteger, VARCHAR, DateTime, Boolean,
                        Integer, String, ForeignKey, Numeric, Text, JSON)
from sqlalchemy.dialects.postgresql import NUMERIC
from sqlalchemy_json import NestedMutableJson
from sqlalchemy_serializer import SerializerMixin
from .. import db_client

class NotificationAction(db_client.Model, SerializerMixin):
    __tablename__ = 'notification_action'
    action_id = Column(BigInteger, primary_key=True)
    action_name = Column(VARCHAR(255), nullable=False)

class NotificationCompany(db_client.Model,SerializerMixin):
    __tablename__ = 'notification_company'
    id = Column(BigInteger, primary_key=True)
    company_id = Column(BigInteger)
    action_id = Column(BigInteger)
    modified_by = Column(VARCHAR(255))
    modified_on = Column(DateTime, default=datetime.datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    deleted = Column(Boolean, default=False)

class NotificationUser(db_client.Model, SerializerMixin):
    __tablename__ = 'notification_user'
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger)
    action_id = Column(BigInteger)
    company_id = Column(BigInteger)
    email = Column(VARCHAR(255))
    modified_by = Column(VARCHAR(255))
    modified_on = Column(DateTime, default=datetime.datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    deleted = Column(Boolean, default=False)

class NotificationUserMessage(db_client.Model, SerializerMixin):
    __tablename__ = 'notification_user_message'
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger)
    company_id = Column(BigInteger)
    action_id = Column(BigInteger)
    message = Column(JSON)
    is_read = Column(Boolean, default=False)
    created_on = Column(DateTime, default=datetime.datetime.utcnow)
    created_by = Column(VARCHAR(255))
    modified_by = Column(VARCHAR(255))
    modified_on = Column(DateTime)
    deleted_at = Column(DateTime, nullable=True)
    deleted = Column(Boolean, default=False)

# db_client.create_all()