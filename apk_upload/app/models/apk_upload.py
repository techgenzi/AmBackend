from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, Boolean, Date
from sqlalchemy_serializer import SerializerMixin

from .. import db_client


class APKUpload(db_client.Model, SerializerMixin):
    __tablename__ = 'apk_upload'

    apk_upload_id = Column(BigInteger, primary_key=True)
    title = Column(VARCHAR(255))
    description = Column(VARCHAR(255))
    media_key = Column(VARCHAR(255))
    form_type = Column(VARCHAR(255))
    upload_date = Column(Date)
    file_size = Column(VARCHAR(255))
    active = Column(Boolean)
    app_id = Column(VARCHAR(255))
    version_name = Column(VARCHAR(255))
    version_no = Column(VARCHAR(255))
    compcode = Column(BigInteger)
    modified_by = Column(VARCHAR(100))
    modified_on = Column(DateTime)
    created_by = Column(VARCHAR(100))
    created_on = Column(DateTime)
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)


db_client.create_all()
