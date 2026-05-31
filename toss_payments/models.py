"""Toss Payments models — payment + cash receipt."""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Numeric, String

from vbwd.extensions import db
from vbwd.models.base import TzAwareTimestampMixin


class TossPayment(TzAwareTimestampMixin, db.Model):
    __tablename__ = "toss_payments"

    id = Column(
        db.UUID,
        primary_key=True,
        server_default=db.text("gen_random_uuid()"),
    )
    order_id = Column(String(64), nullable=False, unique=True, index=True)
    payment_key = Column(String(128), nullable=True, index=True)
    method = Column(String(32), nullable=True)
    amount = Column(Numeric(14, 0), nullable=False)
    currency = Column(String(3), nullable=False, default="KRW")
    status = Column(String(24), nullable=False, default="pending")
    last_provider_status = Column(String(32), nullable=True)
    extra_data = Column(db.JSON, nullable=True)
    # created_at / updated_at provided by TzAwareTimestampMixin (S20).

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "order_id": self.order_id,
            "payment_key": self.payment_key,
            "method": self.method,
            "amount": str(self.amount),
            "currency": self.currency,
            "status": self.status,
            "last_provider_status": self.last_provider_status,
            "extra_data": self.extra_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TossCashReceipt(db.Model):
    __tablename__ = "toss_payments_cash_receipts"

    id = Column(
        db.UUID,
        primary_key=True,
        server_default=db.text("gen_random_uuid()"),
    )
    receipt_id = Column(String(128), nullable=True, index=True)
    payment_key = Column(String(128), nullable=False, index=True)
    identifier_type = Column(String(16), nullable=False)
    identifier_hash = Column(String(64), nullable=False)
    receipt_type = Column(String(16), nullable=False)
    status = Column(String(16), nullable=False, default="issued")
    issued_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "receipt_id": self.receipt_id,
            "payment_key": self.payment_key,
            "identifier_type": self.identifier_type,
            "identifier_hash": self.identifier_hash,
            "receipt_type": self.receipt_type,
            "status": self.status,
            "issued_at": self.issued_at.isoformat() if self.issued_at else None,
            "cancelled_at": (
                self.cancelled_at.isoformat() if self.cancelled_at else None
            ),
        }
