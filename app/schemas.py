from pydantic import BaseModel, Field


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=64)


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    username: str

    model_config = {"from_attributes": True}


class ProductOut(BaseModel):
    id: int
    sku: str
    name: str
    description: str
    price_cent: int
    stock: int

    model_config = {"from_attributes": True}


class CartItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0, le=99)


class CartItemOut(BaseModel):
    product_id: int
    sku: str
    name: str
    price_cent: int
    quantity: int
    subtotal_cent: int


class CartOut(BaseModel):
    items: list[CartItemOut]
    total_cent: int


class OrderCreateIn(BaseModel):
    # 为空则从购物车结算；传入则按指定商品下单
    items: list[CartItemIn] | None = None


class OrderItemOut(BaseModel):
    sku: str
    name: str
    unit_price_cent: int
    quantity: int
    subtotal_cent: int


class OrderOut(BaseModel):
    id: int
    order_no: str
    status: str
    total_cent: int
    items: list[OrderItemOut]
    created_at: str | None = None


class PaymentWebhookIn(BaseModel):
    event_id: str
    order_no: str
    amount_cent: int
    status: str = "success"
