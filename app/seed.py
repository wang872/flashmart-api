from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Product, User
from app.security import hash_password
from app.services.cache import cache


def seed_data(db: Session) -> None:
    if db.scalar(select(User.id).limit(1)) is not None:
        return

    alice = User(username="alice", password_hash=hash_password("alice123"))
    bob = User(username="bob", password_hash=hash_password("bob123"))
    db.add_all([alice, bob])
    db.add_all(
        [
            Product(
                sku="PHONE-X",
                name="Nova Phone X",
                description="旗舰机，演示库存扣减与并发下单",
                price_cent=599900,
                stock=10,
                version=0,
            ),
            Product(
                sku="BUD-PRO",
                name="Pulse Buds Pro",
                description="降噪耳机",
                price_cent=129900,
                stock=50,
                version=0,
            ),
            Product(
                sku="CABLE-C",
                name="USB-C 数据线",
                description="低价高库存 SKU",
                price_cent=1999,
                stock=200,
                version=0,
            ),
        ]
    )
    db.commit()
    cache.clear()
