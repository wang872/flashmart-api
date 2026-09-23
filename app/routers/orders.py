from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, get_idempotency_key
from app.models import Order, User
from app.schemas import OrderCreateIn
from app.services import order as order_svc

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("")
def create_order(
    body: OrderCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    idempotency_key: str = Depends(get_idempotency_key),
):
    items = [i.model_dump() for i in body.items] if body.items else None
    order = order_svc.create_order(db, user, items, idempotency_key)
    return order_svc.serialize_order(db, order)


@router.get("")
def list_orders(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    orders = db.scalars(select(Order).where(Order.user_id == user.id).order_by(Order.id.desc())).all()
    return [order_svc.serialize_order(db, o) for o in orders]


@router.get("/{order_no}")
def get_order(order_no: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    order = order_svc.get_order(db, user, order_no)
    return order_svc.serialize_order(db, order)


@router.post("/{order_no}/cancel")
def cancel_order(order_no: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    order = order_svc.cancel_order(db, user, order_no)
    return order_svc.serialize_order(db, order)
