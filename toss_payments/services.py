"""Toss Payments services — domain mapping + webhook handling + PII hashing."""
import hashlib
from decimal import Decimal
from typing import Any, Dict, Optional

from vbwd.extensions import db

from plugins.toss_payments.toss_payments.models import (
    TossCashReceipt,
    TossPayment,
)


STATUS_MAP = {
    "DONE": "completed",
    "CANCELED": "cancelled",
    "PARTIAL_CANCELED": "refunded",
    "ABORTED": "failed",
    "EXPIRED": "failed",
    "READY": "pending",
    "IN_PROGRESS": "processing",
    "WAITING_FOR_DEPOSIT": "pending",
}


def map_toss_status(provider_status: str) -> str:
    if not provider_status:
        return "failed"
    return STATUS_MAP.get(provider_status.upper(), "failed")


def hash_identifier(identifier: str) -> str:
    """Privacy-preserving hash for cash-receipt identifiers.

    Why: phone / CPF / biz-reg-no are PII — we don't store plaintext so
    admins only see the hash, not the actual phone number.
    """
    return hashlib.sha256(identifier.encode()).hexdigest()


class TossPaymentService:
    def __init__(self, session=None):
        self._session = session or db.session

    def record_payment_confirmed(
        self,
        order_id: str,
        payment_key: str,
        method: str,
        amount: Decimal,
        provider_status: str,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> TossPayment:
        payment = self._get_or_create(order_id)
        payment.payment_key = payment_key
        payment.method = method
        payment.amount = amount
        payment.currency = "KRW"
        payment.status = map_toss_status(provider_status)
        payment.last_provider_status = provider_status
        payment.extra_data = extra_data
        self._session.add(payment)
        self._session.commit()
        return payment

    def apply_provider_update(
        self, order_id: str, provider_payload: Dict[str, Any]
    ) -> TossPayment:
        payment = self._get_or_create(order_id)
        provider_status = provider_payload.get("status", "")
        new_status = map_toss_status(provider_status)

        if (
            payment.status == new_status
            and payment.last_provider_status == provider_status
        ):
            return payment

        payment.status = new_status
        payment.last_provider_status = provider_status
        if provider_payload.get("paymentKey"):
            payment.payment_key = provider_payload["paymentKey"]
        self._session.commit()
        return payment

    def _get_or_create(self, order_id: str) -> TossPayment:
        payment = (
            self._session.query(TossPayment)
            .filter_by(order_id=order_id)
            .one_or_none()
        )
        if payment is None:
            payment = TossPayment(
                order_id=order_id, amount=Decimal("0"), currency="KRW"
            )
        return payment


class TossCashReceiptService:
    """Cash receipt issuance + ledger.

    Stores only the hash of the identifier (phone/biz-reg-no) — the
    plaintext is sent to Toss at issuance and then forgotten.
    """

    ALLOWED_IDENTIFIER_TYPES = ("phone", "business")
    ALLOWED_RECEIPT_TYPES = ("소득공제", "지출증빙")

    def __init__(self, session=None):
        self._session = session or db.session

    def record_receipt(
        self,
        payment_key: str,
        identifier_type: str,
        identifier: str,
        receipt_type: str,
        receipt_id: Optional[str] = None,
    ) -> TossCashReceipt:
        if identifier_type not in self.ALLOWED_IDENTIFIER_TYPES:
            raise ValueError(
                f"identifier_type must be one of "
                f"{self.ALLOWED_IDENTIFIER_TYPES}"
            )
        if receipt_type not in self.ALLOWED_RECEIPT_TYPES:
            raise ValueError(
                f"receipt_type must be one of {self.ALLOWED_RECEIPT_TYPES}"
            )

        receipt = TossCashReceipt(
            receipt_id=receipt_id,
            payment_key=payment_key,
            identifier_type=identifier_type,
            identifier_hash=hash_identifier(identifier),
            receipt_type=receipt_type,
            status="issued",
        )
        self._session.add(receipt)
        self._session.commit()
        return receipt


class TossWebhookHandler:
    def __init__(self, service: Optional[TossPaymentService] = None):
        self._service = service or TossPaymentService()

    def handle(self, payload: Dict[str, Any]) -> TossPayment:
        order_id = payload.get("orderId") or payload.get("order_id")
        if not order_id:
            raise ValueError("missing orderId in Toss webhook")
        return self._service.apply_provider_update(order_id, payload)
