import json

from fastapi.testclient import TestClient

from app.security import sign_webhook


def _product_id(client: TestClient, sku: str) -> int:
    products = client.get("/products").json()
    return next(p["id"] for p in products if p["sku"] == sku)


def test_register_login_me(client: TestClient) -> None:
    reg = client.post("/auth/register", json={"username": "carol", "password": "carol123"})
    assert reg.status_code == 200
    login = client.post("/auth/login", json={"username": "carol", "password": "carol123"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "carol"


def test_cart_and_checkout_from_cart(client: TestClient, login) -> None:
    headers = login("alice", "alice123")
    pid = _product_id(client, "CABLE-C")
    put = client.put("/cart", json={"product_id": pid, "quantity": 2}, headers=headers)
    assert put.status_code == 200
    assert put.json()["total_cent"] == 1999 * 2

    created = client.post(
        "/orders",
        json={},
        headers={**headers, "Idempotency-Key": "alice-order-1"},
    )
    assert created.status_code == 200
    body = created.json()
    assert body["status"] == "pending_pay"
    assert body["total_cent"] == 3998
    assert len(body["items"]) == 1

    cart = client.get("/cart", headers=headers)
    assert cart.json()["items"] == []


def test_idempotent_create_order(client: TestClient, login) -> None:
    headers = login("alice", "alice123")
    pid = _product_id(client, "BUD-PRO")
    payload = {"items": [{"product_id": pid, "quantity": 1}]}
    first = client.post("/orders", json=payload, headers={**headers, "Idempotency-Key": "same-key"})
    second = client.post("/orders", json=payload, headers={**headers, "Idempotency-Key": "same-key"})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["order_no"] == second.json()["order_no"]


def test_stock_conflict_and_cancel_restore(client: TestClient, login) -> None:
    headers = login("alice", "alice123")
    pid = _product_id(client, "PHONE-X")
    too_many = client.post(
        "/orders",
        json={"items": [{"product_id": pid, "quantity": 99}]},
        headers={**headers, "Idempotency-Key": "over-stock"},
    )
    assert too_many.status_code == 409

    before = next(p for p in client.get("/products").json() if p["id"] == pid)
    created = client.post(
        "/orders",
        json={"items": [{"product_id": pid, "quantity": 2}]},
        headers={**headers, "Idempotency-Key": "phone-2"},
    )
    assert created.status_code == 200
    after = next(p for p in client.get("/products").json() if p["id"] == pid)
    assert after["stock"] == before["stock"] - 2

    cancelled = client.post(f"/orders/{created.json()['order_no']}/cancel", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    restored = next(p for p in client.get("/products").json() if p["id"] == pid)
    assert restored["stock"] == before["stock"]


def test_payment_webhook_hmac_and_replay(client: TestClient, login) -> None:
    headers = login("bob", "bob123")
    pid = _product_id(client, "CABLE-C")
    created = client.post(
        "/orders",
        json={"items": [{"product_id": pid, "quantity": 1}]},
        headers={**headers, "Idempotency-Key": "pay-me"},
    )
    order = created.json()
    payload = {
        "event_id": "evt_001",
        "order_no": order["order_no"],
        "amount_cent": order["total_cent"],
        "status": "success",
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    sig = sign_webhook(raw, "test-webhook-secret")

    bad = client.post("/payments/webhook", content=raw, headers={"X-Payment-Signature": "deadbeef"})
    assert bad.status_code == 401

    ok = client.post("/payments/webhook", content=raw, headers={"Content-Type": "application/json", "X-Payment-Signature": sig})
    assert ok.status_code == 200
    assert ok.json()["status"] == "paid"

    replay = client.post("/payments/webhook", content=raw, headers={"Content-Type": "application/json", "X-Payment-Signature": sig})
    assert replay.status_code == 200
    assert replay.json()["order_no"] == order["order_no"]
    assert replay.json()["status"] == "paid"
