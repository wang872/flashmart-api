from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import Base, get_engine, get_session_factory
from app.routers import auth, cart, orders, payments, products
from app.seed import seed_data
from app.services.cache import cache


@asynccontextmanager
async def lifespan(_app: FastAPI):
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    cache.clear()
    if get_settings().seed_on_startup:
        db = get_session_factory()()
        try:
            seed_data(db)
        finally:
            db.close()
    yield


app = FastAPI(
    title="FlashMart API",
    description="电商订单后端：JWT、购物车、乐观锁库存、下单幂等、支付回调。",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(payments.router)


@app.get("/health")
def health():
    return {"status": "ok"}
