from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import order as order_svc

router = APIRouter(prefix="/products", tags=["products"])


@router.get("")
def list_products(db: Session = Depends(get_db)):
    return order_svc.list_products(db)
