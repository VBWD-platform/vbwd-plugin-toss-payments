# Toss Payments Plugin (Backend)

Direct Toss Payments integration for Korean merchants — widget-hosted
checkout with cards + KakaoPay + Naver Pay + Samsung Pay + bank
transfer.

## Purpose

Two-phase flow: client-side widget returns a `paymentKey`, the backend
calls `POST /v1/payments/confirm` server-side. Basic-auth header
`Authorization: Basic base64(secretKey:)`.

Handles Korean cash-receipt (현금영수증) issuance with PII-safe
identifier hashing — plaintext phone/biz-id is sent to Toss at
issuance and then forgotten; only SHA-256 hash is persisted.

## API Routes

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/v1/plugins/toss-payments/payments/confirm` | Bearer | Server-side confirm |
| GET | `/api/v1/plugins/toss-payments/payments/:order/status` | Bearer | Refresh status |
| POST | `/api/v1/plugins/toss-payments/webhooks` | HMAC | Webhook receiver |
| POST | `/api/v1/plugins/toss-payments/cash-receipts` | Bearer | Issue cash receipt |
| POST | `/api/v1/plugins/toss-payments/payments/:order/refund` | Admin | Cancel (full/partial) |

## Database

- `toss_payments` — payment record per order_id.
- `toss_payments_cash_receipts` — receipt ledger with identifier hash only.

## Frontend bundles

- User: [`vbwd-fe-user-plugin-toss-payments`](https://github.com/VBWD-platform/vbwd-fe-user-plugin-toss-payments)
- Admin: [`vbwd-fe-admin-plugin-toss-payments`](https://github.com/VBWD-platform/vbwd-fe-admin-plugin-toss-payments)

---

**Core:** [vbwd-backend](https://github.com/VBWD-platform/vbwd-backend)

## Documentation

Full platform documentation lives at **[vbwd.cc/docs](https://vbwd.cc/docs)**.

- [Plugin system](https://vbwd.cc/docs-plugin-system) — how backend plugins are registered, enabled, and configured
- [Payments](https://vbwd.cc/docs-core-payments) — documentation for this plugin's domain
- [Architecture](https://vbwd.cc/docs-architecture) — platform layering and the core-agnosticism rule
- [Getting started](https://vbwd.cc/docs-getting-started) — install a VBWD instance and enable plugins
