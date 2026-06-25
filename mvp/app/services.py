from __future__ import annotations

import json
import sqlite3
from datetime import date
from typing import Any

from fastapi import HTTPException, status

from .schemas import InboundReceiptIn, MaterialIn, OutboundOrderIn, PartnerIn, TemperatureAlertIn


TODAY = date.today


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def rows_to_list(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def audit(
    conn: sqlite3.Connection,
    *,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: str | int,
    reason: str,
    payload: dict[str, Any],
) -> None:
    conn.execute(
        """
        INSERT INTO audit_trail(actor, action, entity_type, entity_id, reason, payload)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (actor, action, entity_type, str(entity_id), reason, json.dumps(payload, ensure_ascii=False, sort_keys=True)),
    )


def _parse_scope(scope_codes: str) -> set[str]:
    return {item.strip() for item in scope_codes.split(",") if item.strip()}


def _assert_not_expired(value: str, message: str) -> None:
    if date.fromisoformat(value) < TODAY():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)


def get_material(conn: sqlite3.Connection, code: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM materials WHERE code = ?", (code,)).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"material not found: {code}")
    return row


def get_partner(conn: sqlite3.Connection, code: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM partners WHERE code = ?", (code,)).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"partner not found: {code}")
    return row


def assert_partner_allowed(conn: sqlite3.Connection, *, partner_code: str, expected_type: str, material: sqlite3.Row) -> sqlite3.Row:
    partner = get_partner(conn, partner_code)
    if partner["partner_type"] not in {expected_type, "both"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"partner {partner_code} is not a valid {expected_type}",
        )
    _assert_not_expired(partner["license_valid_until"], f"partner license expired: {partner_code}")
    if material["category_code"] not in _parse_scope(partner["scope_codes"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"GSP scope blocked: partner {partner_code} cannot handle "
                f"device category {material['category_code']}"
            ),
        )
    return partner


def assert_material_sellable(material: sqlite3.Row) -> None:
    _assert_not_expired(material["registration_valid_until"], f"registration expired: {material['code']}")


def upsert_material(conn: sqlite3.Connection, payload: MaterialIn) -> dict[str, Any]:
    conn.execute(
        """
        INSERT INTO materials(code, name, category_code, registration_no, registration_valid_until, sn_control, temp_zone, storage_rules)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(code) DO UPDATE SET
            name = excluded.name,
            category_code = excluded.category_code,
            registration_no = excluded.registration_no,
            registration_valid_until = excluded.registration_valid_until,
            sn_control = excluded.sn_control,
            temp_zone = excluded.temp_zone,
            storage_rules = excluded.storage_rules
        """,
        (
            payload.code,
            payload.name,
            payload.category_code,
            payload.registration_no,
            payload.registration_valid_until.isoformat(),
            int(payload.sn_control),
            payload.temp_zone,
            payload.storage_rules,
        ),
    )
    audit(
        conn,
        actor="system",
        action="UPSERT_MATERIAL",
        entity_type="material",
        entity_id=payload.code,
        reason="master data sync/manual upsert",
        payload=payload.model_dump(mode="json"),
    )
    return row_to_dict(get_material(conn, payload.code)) or {}


def upsert_partner(conn: sqlite3.Connection, payload: PartnerIn) -> dict[str, Any]:
    scope_codes = ",".join(payload.scope_codes)
    conn.execute(
        """
        INSERT INTO partners(code, name, partner_type, scope_codes, license_valid_until)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(code) DO UPDATE SET
            name = excluded.name,
            partner_type = excluded.partner_type,
            scope_codes = excluded.scope_codes,
            license_valid_until = excluded.license_valid_until
        """,
        (payload.code, payload.name, payload.partner_type, scope_codes, payload.license_valid_until.isoformat()),
    )
    audit(
        conn,
        actor="system",
        action="UPSERT_PARTNER",
        entity_type="partner",
        entity_id=payload.code,
        reason="master data sync/manual upsert",
        payload=payload.model_dump(mode="json"),
    )
    return row_to_dict(get_partner(conn, payload.code)) or {}


def receive_inventory(conn: sqlite3.Connection, payload: InboundReceiptIn) -> dict[str, Any]:
    material = get_material(conn, payload.material_code)
    assert_material_sellable(material)
    assert_partner_allowed(conn, partner_code=payload.supplier_code, expected_type="supplier", material=material)

    if int(material["sn_control"]) == 1:
        if len(payload.serial_numbers) != payload.quantity:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="SN-controlled material requires one serial number per inbound unit",
            )
        if len(set(payload.serial_numbers)) != len(payload.serial_numbers):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="duplicate serial numbers in request")

    cursor = conn.execute(
        """
        INSERT INTO inventory(material_code, warehouse_code, location_code, lot_no, expires_at, quantity)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            payload.material_code,
            payload.warehouse_code,
            payload.location_code,
            payload.lot_no,
            payload.expires_at.isoformat(),
            payload.quantity,
        ),
    )
    inventory_id = cursor.lastrowid

    for serial_no in payload.serial_numbers:
        conn.execute(
            "INSERT INTO serial_inventory(inventory_id, serial_no, status) VALUES (?, ?, 'available')",
            (inventory_id, serial_no),
        )

    audit(
        conn,
        actor=payload.actor,
        action="RECEIVE_INVENTORY",
        entity_type="inventory",
        entity_id=inventory_id,
        reason=payload.reason,
        payload=payload.model_dump(mode="json"),
    )
    return {"inventory_id": inventory_id, "received_quantity": payload.quantity, "status": "available"}


def allocate_outbound(conn: sqlite3.Connection, payload: OutboundOrderIn) -> dict[str, Any]:
    material = get_material(conn, payload.material_code)
    assert_material_sellable(material)
    assert_partner_allowed(conn, partner_code=payload.customer_code, expected_type="customer", material=material)

    candidates = conn.execute(
        """
        SELECT * FROM inventory
        WHERE material_code = ? AND warehouse_code = ? AND quantity > 0 AND locked = 0
        ORDER BY expires_at ASC, id ASC
        """,
        (payload.material_code, payload.warehouse_code),
    ).fetchall()

    remaining = payload.quantity
    plan: list[dict[str, Any]] = []
    for row in candidates:
        if remaining <= 0:
            break
        picked = min(int(row["quantity"]), remaining)
        plan.append({"inventory": row, "quantity": picked})
        remaining -= picked

    if remaining > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"insufficient unlocked inventory: shortage={remaining}",
        )

    order_cursor = conn.execute(
        """
        INSERT INTO outbound_orders(customer_code, material_code, warehouse_code, quantity, status)
        VALUES (?, ?, ?, ?, 'allocated')
        """,
        (payload.customer_code, payload.material_code, payload.warehouse_code, payload.quantity),
    )
    order_id = order_cursor.lastrowid
    allocations: list[dict[str, Any]] = []
    serials: list[str] = []

    for item in plan:
        inv = item["inventory"]
        qty = int(item["quantity"])
        conn.execute("UPDATE inventory SET quantity = quantity - ? WHERE id = ?", (qty, inv["id"]))
        conn.execute(
            """
            INSERT INTO outbound_allocations(order_id, inventory_id, quantity, lot_no, expires_at, location_code)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (order_id, inv["id"], qty, inv["lot_no"], inv["expires_at"], inv["location_code"]),
        )

        if int(material["sn_control"]) == 1:
            selected_serials = conn.execute(
                """
                SELECT serial_no FROM serial_inventory
                WHERE inventory_id = ? AND status = 'available'
                ORDER BY id ASC
                LIMIT ?
                """,
                (inv["id"], qty),
            ).fetchall()
            if len(selected_serials) < qty:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="serial inventory is inconsistent")
            selected_values = [row["serial_no"] for row in selected_serials]
            conn.executemany(
                "UPDATE serial_inventory SET status = 'shipped' WHERE serial_no = ?",
                [(serial_no,) for serial_no in selected_values],
            )
            serials.extend(selected_values)

        allocations.append(
            {
                "inventory_id": inv["id"],
                "lot_no": inv["lot_no"],
                "expires_at": inv["expires_at"],
                "location_code": inv["location_code"],
                "quantity": qty,
            }
        )

    source_location = allocations[0]["location_code"] if allocations else "UNKNOWN"
    agv_cursor = conn.execute(
        """
        INSERT INTO agv_tasks(order_id, source_location, target_location, status)
        VALUES (?, ?, 'OUTBOUND_DOCK', 'created')
        """,
        (order_id, source_location),
    )
    agv_task_id = agv_cursor.lastrowid

    audit(
        conn,
        actor=payload.actor,
        action="ALLOCATE_OUTBOUND",
        entity_type="outbound_order",
        entity_id=order_id,
        reason=payload.reason,
        payload={**payload.model_dump(mode="json"), "allocations": allocations, "serial_numbers": serials},
    )
    audit(
        conn,
        actor="system",
        action="CREATE_AGV_TASK",
        entity_type="agv_task",
        entity_id=agv_task_id,
        reason="pick-to-dock movement",
        payload={"order_id": order_id, "source_location": source_location, "target_location": "OUTBOUND_DOCK"},
    )

    return {
        "order_id": order_id,
        "status": "allocated",
        "allocations": allocations,
        "serial_numbers": serials,
        "agv_task": {"id": agv_task_id, "status": "created", "source_location": source_location, "target_location": "OUTBOUND_DOCK"},
    }


def lock_location_for_temperature(conn: sqlite3.Connection, payload: TemperatureAlertIn) -> dict[str, Any]:
    rows = conn.execute(
        """
        SELECT id FROM inventory
        WHERE warehouse_code = ? AND location_code = ? AND quantity > 0 AND locked = 0
        """,
        (payload.warehouse_code, payload.location_code),
    ).fetchall()
    inventory_ids = [row["id"] for row in rows]

    if inventory_ids:
        conn.executemany(
            "UPDATE inventory SET locked = 1, lock_reason = ? WHERE id = ?",
            [(payload.reason, inventory_id) for inventory_id in inventory_ids],
        )
        conn.executemany(
            "UPDATE serial_inventory SET status = 'locked' WHERE inventory_id = ? AND status = 'available'",
            [(inventory_id,) for inventory_id in inventory_ids],
        )

    audit(
        conn,
        actor=payload.actor,
        action="LOCK_LOCATION_TEMPERATURE_ALERT",
        entity_type="location",
        entity_id=f"{payload.warehouse_code}/{payload.location_code}",
        reason=payload.reason,
        payload={**payload.model_dump(mode="json"), "locked_inventory_ids": inventory_ids},
    )
    return {"locked_inventory_ids": inventory_ids, "locked_count": len(inventory_ids)}
