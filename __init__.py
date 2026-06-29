"""Toss Payments plugin — Korean aggregator (cards + KakaoPay + Naver Pay + cash receipts)."""
from typing import Optional, Dict, Any, TYPE_CHECKING
from decimal import Decimal
from uuid import UUID

from vbwd.plugins.base import PluginMetadata
from vbwd.plugins.payment_provider import (
    PaymentProviderPlugin,
    PaymentResult,
    PaymentStatus,
)

if TYPE_CHECKING:
    from flask import Blueprint


DEFAULT_CONFIG = {
    "sandbox": True,
    "test_client_key": "",
    "test_secret_key": "",
    "test_api_url": "https://api.tosspayments.com/v1",
    "live_client_key": "",
    "live_secret_key": "",
    "live_api_url": "https://api.tosspayments.com/v1",
    "enabled_methods": ["CARD", "KAKAOPAY", "NAVERPAY", "SAMSUNGPAY", "TRANSFER"],
    "currency": "KRW",
    "cash_receipt_enabled": True,
    "tax_invoice_enabled": False,
}


class TossPaymentsPlugin(PaymentProviderPlugin):
    """Toss Payments — Korean two-phase (request → confirm) flow.

    Class MUST live in __init__.py per plugin-discovery rule.
    """

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="toss_payments",
            version="26.6.1",
            author="VBWD Team",
            description=(
                "Toss Payments (Korea) — cards + KakaoPay + Naver Pay + "
                "Samsung Pay + bank transfer; two-phase confirm; "
                "cash-receipt (현금영수증) issuance."
            ),
            dependencies=[],
        )

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        merged = {**DEFAULT_CONFIG}
        if config:
            merged.update(config)
        super().initialize(merged)

    def get_blueprint(self) -> Optional["Blueprint"]:
        from plugins.toss_payments.toss_payments.routes import toss_plugin_bp

        return toss_plugin_bp

    def get_url_prefix(self) -> Optional[str]:
        return "/api/v1/plugins/toss-payments"

    @property
    def admin_permissions(self):
        return [
            {
                "key": "payments.configure",
                "label": "Payment provider settings",
                "group": "Payments",
            },
        ]

    def on_enable(self) -> None:
        pass

    def on_disable(self) -> None:
        pass

    def _get_adapter(self):
        from flask import current_app
        from plugins.toss_payments.toss_payments.sdk_adapter import (
            TossPaymentsSDKAdapter,
        )
        from vbwd.sdk.interface import SDKConfig

        config_store = current_app.config_store
        config = config_store.get_config("toss_payments")
        prefix = "test_" if config.get("sandbox", True) else "live_"
        return TossPaymentsSDKAdapter(
            SDKConfig(
                api_key=config.get(f"{prefix}secret_key", ""),
                sandbox=config.get("sandbox", True),
            ),
            client_key=config.get(f"{prefix}client_key", ""),
            api_url=config.get(f"{prefix}api_url", DEFAULT_CONFIG[f"{prefix}api_url"]),
        )

    def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        subscription_id: UUID,
        user_id: UUID,
        metadata: Optional[Dict[str, Any]] = None,
        capture: bool = True,
    ) -> PaymentResult:
        if currency.upper() != "KRW":
            return PaymentResult(
                success=False,
                status=PaymentStatus.FAILED,
                error_message=(f"Toss Payments supports KRW only, got {currency}"),
            )
        if int(amount) != amount:
            return PaymentResult(
                success=False,
                status=PaymentStatus.FAILED,
                error_message="KRW requires integer amounts (no sub-unit)",
            )
        return PaymentResult(
            success=True,
            transaction_id=str(subscription_id),
            status=PaymentStatus.PENDING,
            metadata={
                "order_id": str(subscription_id),
                "amount": int(amount),
                "client_key": self._config_client_key(),
            },
        )

    def capture_payment(
        self, payment_id: str, amount: Optional[Decimal] = None
    ) -> PaymentResult:
        return PaymentResult(
            success=False,
            status=PaymentStatus.FAILED,
            error_message=("Toss captures via payment/confirm on the return URL"),
        )

    def release_authorization(self, payment_id: str) -> PaymentResult:
        return PaymentResult(
            success=False,
            status=PaymentStatus.FAILED,
            error_message=("Toss does not expose authorization release via preference"),
        )

    def process_payment(
        self, payment_intent_id: str, payment_method: str
    ) -> PaymentResult:
        return PaymentResult(
            success=False,
            status=PaymentStatus.FAILED,
            error_message=(
                "Call confirm_payment on the route with paymentKey + "
                "orderId + amount from the widget return URL"
            ),
        )

    def refund_payment(
        self, transaction_id: str, amount: Optional[Decimal] = None
    ) -> PaymentResult:
        adapter = self._get_adapter()
        response = adapter.cancel_payment(payment_key=transaction_id, amount=amount)
        if not response.success:
            return PaymentResult(
                success=False,
                error_message=response.error,
                status=PaymentStatus.FAILED,
            )
        return PaymentResult(
            success=True,
            transaction_id=transaction_id,
            status=PaymentStatus.REFUNDED,
        )

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        adapter = self._get_adapter()
        return adapter.verify_webhook(payload, signature)

    def handle_webhook(self, payload: Dict[str, Any]) -> None:
        from plugins.toss_payments.toss_payments.services import (
            TossWebhookHandler,
        )

        TossWebhookHandler().handle(payload)

    def _config_client_key(self) -> str:
        from flask import current_app

        config = current_app.config_store.get_config("toss_payments")
        prefix = "test_" if config.get("sandbox", True) else "live_"
        return config.get(f"{prefix}client_key", "")
