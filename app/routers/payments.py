from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.errors import unauthorized
from app.schemas import PaymentWebhookIn
from app.security import verify_webhook_signature
from app.services import order as order_svc

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/webhook")
async def payment_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_payment_signature: str | None = Header(default=None),
):
    body = await request.body()
    secret = get_settings().payment_webhook_secret
    if not verify_webhook_signature(body, x_payment_signature or "", secret):
        raise unauthorized("支付签名无效")
    payload = PaymentWebhookIn.model_validate_json(body)
    order = order_svc.apply_payment(
        db,
        payload.event_id,
        payload.order_no,
        payload.amount_cent,
        payload.status,
        body.decode("utf-8"),
    )
    return order_svc.serialize_order(db, order)
