"""Toss Payments plugin API routes."""
import logging
from decimal import Decimal

from flask import Blueprint, current_app, jsonify, request

from vbwd.middleware.auth import require_auth

from plugins.toss_payments.toss_payments.services import (
    TossCashReceiptService,
    TossPaymentService,
    TossWebhookHandler,
)

logger = logging.getLogger(__name__)

toss_plugin_bp = Blueprint("toss_plugin", __name__)


def _get_plugin():
    manager = current_app.plugin_manager
    plugin = manager.get_plugin("toss_payments")
    if plugin is None:
        raise RuntimeError("toss_payments plugin not enabled")
    return plugin


@toss_plugin_bp.route("/payments/confirm", methods=["POST"])
@require_auth
def confirm_payment():
    body = request.get_json(silent=True) or {}
    required = ("paymentKey", "orderId", "amount")
    missing = [f for f in required if body.get(f) is None]
    if missing:
        return jsonify({"error": "missing fields", "fields": missing}), 400

    try:
        amount = int(body["amount"])
    except (ValueError, TypeError):
        return jsonify({"error": "invalid amount"}), 400

    plugin = _get_plugin()
    adapter = plugin._get_adapter()
    response = adapter.confirm_payment(
        payment_key=body["paymentKey"],
        order_id=body["orderId"],
        amount=amount,
    )
    if not response.success:
        return jsonify({"error": response.error or "Toss error"}), 502

    service = TossPaymentService()
    service.record_payment_confirmed(
        order_id=body["orderId"],
        payment_key=body["paymentKey"],
        method=response.data.get("method", ""),
        amount=Decimal(str(response.data.get("totalAmount", amount))),
        provider_status=response.data.get("status", ""),
        extra_data=response.data,
    )
    return jsonify(response.data), 200


@toss_plugin_bp.route("/payments/<order_id>/status", methods=["GET"])
@require_auth
def get_status(order_id: str):
    from vbwd.extensions import db

    from plugins.toss_payments.toss_payments.models import TossPayment

    payment = db.session.query(TossPayment).filter_by(order_id=order_id).one_or_none()
    if payment is None:
        return jsonify({"error": "not found"}), 404

    if not payment.payment_key:
        return jsonify(payment.to_dict()), 200

    plugin = _get_plugin()
    response = plugin._get_adapter().get_payment(payment.payment_key)
    if response.success:
        TossPaymentService().apply_provider_update(order_id, response.data)
    return jsonify(payment.to_dict()), 200


@toss_plugin_bp.route("/webhooks", methods=["POST"])
def webhook():
    signature = request.headers.get("toss-signature", "")
    plugin = _get_plugin()
    adapter = plugin._get_adapter()
    if not adapter.verify_webhook(request.get_data(), signature):
        return jsonify({"error": "invalid signature"}), 401

    payload = request.get_json(silent=True) or {}
    TossWebhookHandler().handle(payload)
    return "", 204


@toss_plugin_bp.route("/cash-receipts", methods=["POST"])
@require_auth
def issue_cash_receipt():
    body = request.get_json(silent=True) or {}
    required = ("paymentKey", "identifier_type", "identifier")
    missing = [f for f in required if not body.get(f)]
    if missing:
        return jsonify({"error": "missing fields", "fields": missing}), 400

    plugin = _get_plugin()
    adapter = plugin._get_adapter()
    receipt_type = body.get("receipt_type", "소득공제")
    response = adapter.issue_cash_receipt(
        payment_key=body["paymentKey"],
        identifier_type=body["identifier_type"],
        identifier=body["identifier"],
        receipt_type=receipt_type,
    )
    if not response.success:
        return jsonify({"error": response.error or "Toss error"}), 502

    try:
        service = TossCashReceiptService()
        receipt = service.record_receipt(
            payment_key=body["paymentKey"],
            identifier_type=body["identifier_type"],
            identifier=body["identifier"],
            receipt_type=receipt_type,
            receipt_id=response.data.get("receiptKey"),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(receipt.to_dict()), 201


@toss_plugin_bp.route("/payments/<order_id>/refund", methods=["POST"])
@require_auth
def refund(order_id: str):
    from vbwd.extensions import db

    from plugins.toss_payments.toss_payments.models import TossPayment

    payment = db.session.query(TossPayment).filter_by(order_id=order_id).one_or_none()
    if payment is None or not payment.payment_key:
        return jsonify({"error": "not found"}), 404

    body = request.get_json(silent=True) or {}
    amount = body.get("amount")
    if amount is not None:
        try:
            amount = Decimal(str(amount))
        except (ValueError, ArithmeticError):
            return jsonify({"error": "invalid amount"}), 400

    plugin = _get_plugin()
    response = plugin._get_adapter().cancel_payment(
        payment_key=payment.payment_key, amount=amount
    )
    if not response.success:
        return jsonify({"error": response.error or "Toss error"}), 502
    return jsonify({"payment_key": payment.payment_key}), 200
