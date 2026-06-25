from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import Depends, FastAPI

from .database import get_connection, init_db, transaction
from .schemas import ApiResult, InboundReceiptIn, MaterialIn, OutboundOrderIn, PartnerIn, TemperatureAlertIn
from .services import (
    allocate_outbound,
    lock_location_for_temperature,
    receive_inventory,
    rows_to_list,
    upsert_material,
    upsert_partner,
)

app = FastAPI(
    title="NewWMS Minimal MVP",
    version="0.1.0",
    description="Medical-device GSP WMS MVP: master data, inbound, inventory lock, outbound allocation and AGV task stub.",
)


def get_db() -> sqlite3.Connection:
    conn = get_connection()
    init_db(conn)
    try:
        yield conn
    finally:
        conn.close()


Db = Annotated[sqlite3.Connection, Depends(get_db)]


@app.get("/health", response_model=ApiResult)
def health() -> ApiResult:
    return ApiResult(ok=True, data={"service": "newwms-mvp", "status": "ready"})


@app.post("/master/materials", response_model=ApiResult)
def put_material(payload: MaterialIn, conn: Db) -> ApiResult:
    with transaction(conn):
        data = upsert_material(conn, payload)
    return ApiResult(ok=True, data=data)


@app.post("/master/partners", response_model=ApiResult)
def put_partner(payload: PartnerIn, conn: Db) -> ApiResult:
    with transaction(conn):
        data = upsert_partner(conn, payload)
    return ApiResult(ok=True, data=data)


@app.post("/inbound/receipts", response_model=ApiResult)
def receive(payload: InboundReceiptIn, conn: Db) -> ApiResult:
    with transaction(conn):
        data = receive_inventory(conn, payload)
    return ApiResult(ok=True, data=data)


@app.post("/outbound/orders", response_model=ApiResult)
def outbound(payload: OutboundOrderIn, conn: Db) -> ApiResult:
    with transaction(conn):
        data = allocate_outbound(conn, payload)
    return ApiResult(ok=True, data=data)


@app.post("/quality/temperature-alerts", response_model=ApiResult)
def temperature_alert(payload: TemperatureAlertIn, conn: Db) -> ApiResult:
    with transaction(conn):
        data = lock_location_for_temperature(conn, payload)
    return ApiResult(ok=True, data=data)


@app.get("/inventory", response_model=ApiResult)
def list_inventory(conn: Db) -> ApiResult:
    rows = conn.execute(
        """
        SELECT id, material_code, warehouse_code, location_code, lot_no, expires_at, quantity, locked, lock_reason
        FROM inventory
        ORDER BY warehouse_code, location_code, expires_at, id
        """
    ).fetchall()
    return ApiResult(ok=True, data=rows_to_list(rows))


@app.get("/agv/tasks", response_model=ApiResult)
def list_agv_tasks(conn: Db) -> ApiResult:
    rows = conn.execute(
        """
        SELECT id, order_id, source_location, target_location, status, created_at
        FROM agv_tasks
        ORDER BY id DESC
        """
    ).fetchall()
    return ApiResult(ok=True, data=rows_to_list(rows))


@app.get("/audit-trail", response_model=ApiResult)
def list_audit_trail(conn: Db) -> ApiResult:
    rows = conn.execute(
        """
        SELECT id, actor, action, entity_type, entity_id, reason, payload, created_at
        FROM audit_trail
        ORDER BY id DESC
        LIMIT 200
        """
    ).fetchall()
    return ApiResult(ok=True, data=rows_to_list(rows))
