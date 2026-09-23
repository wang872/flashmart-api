# FlashMart API

一句话介绍：基于 FastAPI 的电商订单后端，覆盖 JWT 鉴权、购物车、乐观锁库存扣减、下单幂等键和 HMAC 支付回调，默认 SQLite 即可本地跑通。

## 技术栈

| 组件 | 说明 |
| --- | --- |
| FastAPI | REST API |
| SQLAlchemy 2.0 | ORM / 乐观锁 `UPDATE ... WHERE version=?` |
| Pydantic v2 | 请求校验 |
| PyJWT | Access Token |
| hashlib PBKDF2 | 密码哈希（无 passlib） |
| 进程内 TTL 缓存 | 接口与 Redis 对齐，可替换 |

## 核心设计

```
下单 ──► Idempotency-Key 命中则直接返回原订单
        │
        ▼
   乐观锁扣库存：WHERE stock>=qty AND version=当前版本
        │ 成功则 version+1，失败 409 让客户端重试
        ▼
   写订单行 + 清空购物车
        │
支付回调 ──► HMAC-SHA256 验签 + event_id 去重（支付通道重复通知）
取消待支付 ──► 回补库存
```

金额一律用 **分（int）**，避免浮点误差。


## 本地运行

Python 3.10+

```powershell
cd g:\自动编程\flashmart-api
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
copy .env.example .env
.venv\Scripts\python -m uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs
- 健康检查: `GET /health`

种子账号：`alice / alice123`、`bob / bob123`。商品：`PHONE-X`、`BUD-PRO`、`CABLE-C`。

```powershell
.venv\Scripts\python -m pytest
```

下单必须带请求头 `Idempotency-Key`。模拟支付：

```powershell
$body = '{"event_id":"evt1","order_no":"替换订单号","amount_cent":1999,"status":"success"}'
# 签名 = HMAC-SHA256(body, PAYMENT_WEBHOOK_SECRET)
```

## API 表

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/auth/register` | 注册 |
| POST | `/auth/login` | 登录拿 JWT |
| GET | `/auth/me` | 当前用户 |
| GET | `/products` | 商品列表（带缓存） |
| GET/PUT | `/cart` | 查看 / 更新购物车 |
| POST | `/orders` | 下单（空 body 则结算购物车） |
| GET | `/orders` `/orders/{order_no}` | 订单列表 / 详情 |
| POST | `/orders/{order_no}/cancel` | 取消待支付并回补库存 |
| POST | `/payments/webhook` | 支付回调（需 `X-Payment-Signature`） |
| GET | `/health` | 健康检查 |



生产环境请修改 `SECRET_KEY` 与 `PAYMENT_WEBHOOK_SECRET`。
