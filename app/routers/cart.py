from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import CartItemIn, CartOut
from app.services import order as order_svc

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("", response_model=CartOut)
def get_cart(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = order_svc.get_cart(db, user)
    return {"items": items, "total_cent": sum(i["subtotal_cent"] for i in items)}


@router.put("", response_model=CartOut)
def put_cart(body: CartItemIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    order_svc.upsert_cart(db, user, body.product_id, body.quantity)
    items = order_svc.get_cart(db, user)
    return {"items": items, "total_cent": sum(i["subtotal_cent"] for i in items)}
