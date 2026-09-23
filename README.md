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

## 简历写法

**中文**

- 基于 FastAPI + SQLAlchemy 2 实现电商订单后端，覆盖注册登录、商品缓存、购物车、下单、取消与支付回调。
- 下单使用乐观锁原子扣减库存，并用 `Idempotency-Key` 保证网络重试不产生重复订单。
- 支付 Webhook 采用 HMAC-SHA256 验签与 `event_id` 去重，防止伪造回调和通道重复通知。
- 商品列表使用可替换的 TTL 缓存接口（默认进程内，可平滑换成 Redis），金额以分为单位存储。

**English**

- Built a FastAPI e-commerce order API with JWT auth, cart checkout, optimistic-lock stock deduction, and idempotent order creation.
- Implemented HMAC-signed payment webhooks with event-id deduplication and stock restore on cancel.
- Used integer cents for money and a Redis-shaped TTL cache for product listings.

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

## 面试可讲点

1. **乐观锁 vs 悲观锁**：高并发抢购用 `version` 条件更新，失败返回 409，避免长事务锁表。
2. **幂等**：同一用户同一 Key 返回同一订单；支付事件用唯一 `event_id`。
3. **钱**：整型分，禁止 float。
4. **回调安全**：共享密钥 HMAC，不信任未签名 body。
5. **缓存失效**：下单/取消后删除 `products:list`。

生产环境请修改 `SECRET_KEY` 与 `PAYMENT_WEBHOOK_SECRET`。
