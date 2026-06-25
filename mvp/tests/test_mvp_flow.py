from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

os.environ["NEWWMS_DB_PATH"] = str(Path("/tmp/newwms_mvp_test.db"))

from app.database import get_connection, init_db, reset_db  # noqa: E402
from app.main import app  # noqa: E402


def client() -> TestClient:
    conn = get_connection(os.environ["NEWWMS_DB_PATH"])
    init_db(conn)
    reset_db(conn)
    conn.close()
    return TestClient(app)


def future(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def seed_master_data(api: TestClient) -> None:
    material = {
        "code": "MD-6846-001",
        "name": "植入类高风险器械",
        "category_code": "6846",
        "registration_no": "械注准20260001",
        "registration_valid_until": future(365),
        "sn_control": True,
        "temp_zone": "refrigerated",
        "storage_rules": "2-8C; keep upright",
    }
    supplier = {
        "code": "SUP-001",
        "name": "合规供应商",
        "partner_type": "supplier",
        "scope_codes": ["6846"],
        "license_valid_until": future(365),
    }
    customer = {
        "code": "CUS-001",
        "name": "合规医院客户",
        "partner_type": "customer",
        "scope_codes": ["6846"],
        "license_valid_until": future(365),
    }
    blocked_customer = {
        "code": "CUS-BLOCKED",
        "name": "超范围客户",
        "partner_type": "customer",
        "scope_codes": ["6815"],
        "license_valid_until": future(365),
    }

    for path, payload in [
        ("/master/materials", material),
        ("/master/partners", supplier),
        ("/master/partners", customer),
        ("/master/partners", blocked_customer),
    ]:
        response = api.post(path, json=payload)
        assert response.status_code == 200, response.text


def test_inbound_outbound_agv_and_audit_flow() -> None:
    api = client()
    seed_master_data(api)

    inbound = {
        "material_code": "MD-6846-001",
        "supplier_code": "SUP-001",
        "warehouse_code": "WH-SH-001",
        "location_code": "COLD-A-01",
        "lot_no": "LOT-202606",
        "expires_at": future(180),
        "quantity": 2,
        "udi": "UDI-DEMO-001",
        "serial_numbers": ["SN-001", "SN-002"],
        "actor": "receiver-a",
        "reason": "purchase receiving",
    }
    response = api.post("/inbound/receipts", json=inbound)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["received_quantity"] == 2

    outbound = {
        "material_code": "MD-6846-001",
        "customer_code": "CUS-001",
        "warehouse_code": "WH-SH-001",
        "quantity": 1,
        "actor": "picker-a",
        "reason": "sales outbound allocation",
    }
    response = api.post("/outbound/orders", json=outbound)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["status"] == "allocated"
    assert data["serial_numbers"] == ["SN-001"]
    assert data["agv_task"]["target_location"] == "OUTBOUND_DOCK"

    inventory = api.get("/inventory").json()["data"]
    assert inventory[0]["quantity"] == 1

    audit = api.get("/audit-trail").json()["data"]
    actions = {row["action"] for row in audit}
    assert "RECEIVE_INVENTORY" in actions
    assert "ALLOCATE_OUTBOUND" in actions
    assert "CREATE_AGV_TASK" in actions


def test_gsp_customer_scope_blocks_outbound() -> None:
    api = client()
    seed_master_data(api)
    response = api.post(
        "/outbound/orders",
        json={
            "material_code": "MD-6846-001",
            "customer_code": "CUS-BLOCKED",
            "warehouse_code": "WH-SH-001",
            "quantity": 1,
        },
    )
    assert response.status_code == 403
    assert "GSP scope blocked" in response.json()["detail"]


def test_temperature_alert_locks_inventory() -> None:
    api = client()
    seed_master_data(api)
    response = api.post(
        "/inbound/receipts",
        json={
            "material_code": "MD-6846-001",
            "supplier_code": "SUP-001",
            "warehouse_code": "WH-SH-001",
            "location_code": "COLD-A-01",
            "lot_no": "LOT-202607",
            "expires_at": future(180),
            "quantity": 1,
            "serial_numbers": ["SN-LOCK-001"],
        },
    )
    assert response.status_code == 200, response.text

    response = api.post(
        "/quality/temperature-alerts",
        json={
            "warehouse_code": "WH-SH-001",
            "location_code": "COLD-A-01",
            "observed_value": 12.1,
            "threshold": "2-8C",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["locked_count"] == 1

    response = api.post(
        "/outbound/orders",
        json={
            "material_code": "MD-6846-001",
            "customer_code": "CUS-001",
            "warehouse_code": "WH-SH-001",
            "quantity": 1,
        },
    )
    assert response.status_code == 409
    assert "insufficient unlocked inventory" in response.json()["detail"]
