from sqlalchemy import Column, VARCHAR, BigInteger, DateTime, Boolean, Text
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy.dialects.postgresql import NUMERIC, JSONB

from .. import db_client


class RejectedMaterial(db_client.Model, SerializerMixin):
    __tablename__ = 'rejected_material'

    rejected_material_id = Column(BigInteger, primary_key=True)
    unique_id       = Column(VARCHAR(50))       # e.g. RJT-000001
    grnotesid       = Column(BigInteger)        # FK → grnotes
    grnlineid       = Column(BigInteger)        # FK → grnlineitems
    product_id      = Column(BigInteger)
    rejected_quantity = Column(NUMERIC)         # = damaged_quantity from QC
    rejection_reason  = Column(JSONB)           # {thickness, size, color}
    rejection_remark  = Column(Text)
    image_attachment  = Column(JSONB)
    # User-selected at QC time:
    # "Return to Store" | "Write Off" | "Re-inspect" | "Return to Vendor" | "Rework"
    action          = Column(VARCHAR(50), default='Return to Store')
    store_id        = Column(BigInteger)        # target store selected by user
    # Processing status (updated later when action is executed)
    # "Pending" | "Completed"
    status          = Column(VARCHAR(50), default='Pending')
    action_date     = Column(DateTime)
    compcode        = Column(BigInteger)
    created_on      = Column(DateTime)
    created_by      = Column(VARCHAR(100))
    modified_on     = Column(DateTime)
    modified_by     = Column(VARCHAR(100))
    deleted         = Column(Boolean, default=False)
    deleted_at      = Column(DateTime)


# db_client.create_all()
