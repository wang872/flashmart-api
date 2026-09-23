import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import bad_request, conflict, not_found
from app.models import CartItem, Order, OrderItem, PaymentEvent, Product, User
from app.services.cache import cache

ALLOWED_TRANSITIONS = {
    "pending_pay": {"paid", "cancelled"},
    "paid": {"shipped", "cancelled"},
    "shipped": {"completed"},
    "completed": set(),
    "cancelled": set(),
}


def _new_order_no() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + uuid.uuid4().hex[:8]


def _invalidate_product_cache() -> None:
    cache.delete("products:list")


def list_products(db: Session) -> list[Product]:
    cached = cache.get_json("products:list")
    if cached is not None:
        # 返回 ORM 对象给路由序列化不方便，路由层直接走缓存 JSON
        return cached
    rows = db.scalars(select(Product).order_by(Product.id)).all()
    payload = [
        {
            "id": p.id,
            "sku": p.sku,
            "name": p.name,
            "description": p.description,
            "price_cent": p.price_cent,
            "stock": p.stock,
        }
        for p in rows
    ]
    cache.set_json("products:list", payload, get_settings().cache_ttl_seconds)
    return payload


def upsert_cart(db: Session, user: User, product_id: int, quantity: int) -> CartItem:
    product = db.get(Product, product_id)
    if not product:
        raise not_found("商品不存在")
    if product.stock < quantity:
        raise conflict(f"库存不足，当前仅剩 {product.stock} 件")
    item = db.scalar(select(CartItem).where(CartItem.user_id == user.id, CartItem.product_id == product_id))
    if item:
        item.quantity = quantity
    else:
        item = CartItem(user_id=user.id, product_id=product_id, quantity=quantity)
        db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_cart(db: Session, user: User) -> list[dict]:
    items = db.scalars(select(CartItem).where(CartItem.user_id == user.id)).all()
    result = []
    for item in items:
        product = db.get(Product, item.product_id)
        if not product:
            continue
        result.append(
            {
                "product_id": product.id,
                "sku": product.sku,
                "name": product.name,
                "price_cent": product.price_cent,
                "quantity": item.quantity,
                "subtotal_cent": product.price_cent * item.quantity,
            }
        )
    return result


def create_order(db: Session, user: User, items: list[dict] | None, idempotency_key: str) -> Order:
    if not idempotency_key:
        raise bad_request("缺少 Idempotency-Key，下单必须带幂等键")

    existing = db.scalar(
        select(Order).where(Order.user_id == user.id, Order.idempotency_key == idempotency_key)
    )
    if existing:
        return existing

    if not items:
        cart = get_cart(db, user)
        if not cart:
            raise bad_request("购物车为空")
        lines = cart
        from_cart = True
    else:
        lines = []
        for raw in items:
            product = db.get(Product, raw["product_id"])
            if not product:
                raise not_found(f"商品 {raw['product_id']} 不存在")
            lines.append(
                {
                    "product_id": product.id,
                    "sku": product.sku,
                    "name": product.name,
                    "price_cent": product.price_cent,
                    "quantity": raw["quantity"],
                }
            )
        from_cart = False

    order = Order(
        order_no=_new_order_no(),
        user_id=user.id,
        status="pending_pay",
        total_cent=0,
        idempotency_key=idempotency_key,
    )
    db.add(order)
    db.flush()

    total = 0
    for line in lines:
        qty = int(line["quantity"])
        # 乐观锁：WHERE stock >= qty AND version = 当前版本，一次原子扣减
        product = db.get(Product, line["product_id"])
        result = db.execute(
            update(Product)
            .where(
                Product.id == product.id,
                Product.stock >= qty,
                Product.version == product.version,
            )
            .values(stock=Product.stock - qty, version=Product.version + 1)
        )
        if result.rowcount != 1:
            db.rollback()
            raise conflict(f"商品 {product.sku} 库存不足或被并发抢购，请重试")
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                sku=product.sku,
                name=product.name,
                unit_price_cent=product.price_cent,
                quantity=qty,
            )
        )
        total += product.price_cent * qty

    order.total_cent = total
    if from_cart:
        db.query(CartItem).filter(CartItem.user_id == user.id).delete()
    db.commit()
    db.refresh(order)
    _invalidate_product_cache()
    return order


def get_order(db: Session, user: User, order_no: str) -> Order:
    order = db.scalar(select(Order).where(Order.order_no == order_no, Order.user_id == user.id))
    if not order:
        raise not_found("订单不存在")
    return order


def cancel_order(db: Session, user: User, order_no: str) -> Order:
    order = get_order(db, user, order_no)
    if order.status != "pending_pay":
        raise conflict("仅待支付订单可取消")
    _restore_stock(db, order)
    order.status = "cancelled"
    db.commit()
    db.refresh(order)
    _invalidate_product_cache()
    return order


def _restore_stock(db: Session, order: Order) -> None:
    items = db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    for item in items:
        db.execute(
            update(Product)
            .where(Product.id == item.product_id)
            .values(stock=Product.stock + item.quantity, version=Product.version + 1)
        )


def apply_payment(db: Session, event_id: str, order_no: str, amount_cent: int, status: str, raw: str) -> Order:
    dup = db.scalar(select(PaymentEvent).where(PaymentEvent.event_id == event_id))
    if dup:
        return dup.order

    order = db.scalar(select(Order).where(Order.order_no == order_no))
    if not order:
        raise not_found("订单不存在")
    if amount_cent != order.total_cent:
        raise bad_request("支付金额与订单金额不一致")
    if status != "success":
        raise bad_request("仅处理 success 支付事件")
    if order.status not in ALLOWED_TRANSITIONS or "paid" not in ALLOWED_TRANSITIONS[order.status]:
        # 已支付则直接幂等返回
        if order.status in {"paid", "shipped", "completed"}:
            return order
        raise conflict(f"订单当前状态 {order.status} 不能标记为已支付")

    order.status = "paid"
    order.paid_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(
        PaymentEvent(
            event_id=event_id,
            order_id=order.id,
            amount_cent=amount_cent,
            status=status,
            raw_payload=raw,
        )
    )
    db.commit()
    db.refresh(order)
    return order


def serialize_order(db: Session, order: Order) -> dict:
    items = db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    return {
        "id": order.id,
        "order_no": order.order_no,
        "status": order.status,
        "total_cent": order.total_cent,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "items": [
            {
                "sku": i.sku,
                "name": i.name,
                "unit_price_cent": i.unit_price_cent,
                "quantity": i.quantity,
                "subtotal_cent": i.unit_price_cent * i.quantity,
            }
            for i in items
        ],
    }
