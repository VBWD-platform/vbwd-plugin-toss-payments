"""Toss Payments SDK adapter — HTTP Basic-auth with secretKey."""
import base64
import hashlib
import hmac
from decimal import Decimal
from typing import Any, Dict, Optional

import requests

from vbwd.sdk.base import BaseSDKAdapter
from vbwd.sdk.interface import SDKConfig, SDKResponse


class TossPaymentsSDKAdapter(BaseSDKAdapter):
    """Toss Payments adapter.

    Uses Basic auth: `Authorization: Basic base64(secretKey + ':')`.
    Liskov: honours BaseSDKAdapter postconditions.
    """

    def __init__(
        self,
        config: SDKConfig,
        client_key: str,
        api_url: str,
        idempotency_service=None,
    ):
        super().__init__(config, idempotency_service)
        self._secret_key = config.api_key
        self._client_key = client_key
        self._api_url = api_url.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "toss_payments"

    def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        metadata: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> SDKResponse:
        return SDKResponse(
            success=True,
            data={
                "order_id": metadata.get("invoice_no", ""),
                "amount": int(amount),
                "client_key": self._client_key,
            },
        )

    def capture_payment(
        self,
        payment_intent_id: str,
        idempotency_key: Optional[str] = None,
    ) -> SDKResponse:
        return self.get_payment(payment_key=payment_intent_id)

    def release_authorization(self, payment_intent_id: str) -> SDKResponse:
        return self.cancel_payment(payment_key=payment_intent_id)

    def get_payment_status(self, payment_intent_id: str) -> SDKResponse:
        return self.get_payment(payment_key=payment_intent_id)

    def refund_payment(
        self,
        payment_intent_id: str,
        amount: Optional[Decimal] = None,
        idempotency_key: Optional[str] = None,
    ) -> SDKResponse:
        return self.cancel_payment(payment_key=payment_intent_id, amount=amount)

    def confirm_payment(
        self, payment_key: str, order_id: str, amount: int
    ) -> SDKResponse:
        """Confirm a payment after the user returns from the Toss widget."""
        return self._post(
            "/payments/confirm",
            {
                "paymentKey": payment_key,
                "orderId": order_id,
                "amount": amount,
            },
        )

    def get_payment(self, payment_key: str) -> SDKResponse:
        return self._get(f"/payments/{payment_key}")

    def cancel_payment(
        self,
        payment_key: str,
        amount: Optional[Decimal] = None,
        reason: str = "고객 요청",
    ) -> SDKResponse:
        """Cancel (refund) a Toss payment — full or partial."""
        payload: Dict[str, Any] = {"cancelReason": reason}
        if amount is not None:
            payload["cancelAmount"] = int(amount)
        return self._post(f"/payments/{payment_key}/cancel", payload)

    def issue_cash_receipt(
        self,
        payment_key: str,
        identifier_type: str,
        identifier: str,
        receipt_type: str = "소득공제",
    ) -> SDKResponse:
        """Issue cash receipt (현금영수증).

        identifier_type: "phone" | "business" (사업자등록번호)
        receipt_type: "소득공제" (income deduction, individual) |
                      "지출증빙" (proof of expense, business)
        """
        payload = {
            "paymentKey": payment_key,
            "type": receipt_type,
            "customerIdentityNumber": identifier,
        }
        return self._post("/cash-receipts", payload)

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify Toss Payments webhook signature header `toss-signature`.

        HMAC-SHA256 over the body keyed by the merchant's secret key.
        """
        if not signature:
            return False
        expected = hmac.new(
            self._secret_key.encode(), payload, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    # ── internal helpers ───────────────────────────────────────────────

    def _post(self, path: str, body: Dict[str, Any]) -> SDKResponse:
        try:
            resp = requests.post(
                f"{self._api_url}{path}",
                json=body,
                headers=self._auth_headers(),
                timeout=30,
            )
        except requests.RequestException as exc:
            return SDKResponse(success=False, error=f"network: {exc}")
        return self._parse(resp)

    def _get(self, path: str) -> SDKResponse:
        try:
            resp = requests.get(
                f"{self._api_url}{path}",
                headers=self._auth_headers(),
                timeout=30,
            )
        except requests.RequestException as exc:
            return SDKResponse(success=False, error=f"network: {exc}")
        return self._parse(resp)

    def _parse(self, resp: requests.Response) -> SDKResponse:
        if resp.status_code >= 500:
            return SDKResponse(
                success=False,
                error=f"Toss {resp.status_code}: {resp.text[:200]}",
            )
        try:
            body = resp.json()
        except ValueError:
            return SDKResponse(success=False, error="invalid JSON from Toss")
        if resp.status_code >= 400:
            return SDKResponse(
                success=False,
                data=body,
                error=body.get("message", f"HTTP {resp.status_code}"),
                error_code=body.get("code"),
            )
        return SDKResponse(success=True, data=body)

    def _auth_headers(self) -> Dict[str, str]:
        token = base64.b64encode(f"{self._secret_key}:".encode()).decode()
        return {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
        }
