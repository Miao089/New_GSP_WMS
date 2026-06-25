from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


DEFAULT_DB_PATH = Path(os.getenv("NEWWMS_DB_PATH", "/tmp/newwms_mvp.db"))


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS materials (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category_code TEXT NOT NULL,
            registration_no TEXT NOT NULL,
            registration_valid_until TEXT NOT NULL,
            sn_control INTEGER NOT NULL DEFAULT 0,
            temp_zone TEXT NOT NULL DEFAULT 'ambient',
            storage_rules TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS partners (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            partner_type TEXT NOT NULL CHECK (partner_type IN ('supplier', 'customer', 'both')),
            scope_codes TEXT NOT NULL,
            license_valid_until TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_code TEXT NOT NULL REFERENCES materials(code),
            warehouse_code TEXT NOT NULL,
            location_code TEXT NOT NULL,
            lot_no TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity >= 0),
            locked INTEGER NOT NULL DEFAULT 0,
            lock_reason TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS serial_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inventory_id INTEGER NOT NULL REFERENCES inventory(id),
            serial_no TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL CHECK (status IN ('available', 'shipped', 'locked')) DEFAULT 'available'
        );

        CREATE TABLE IF NOT EXISTS outbound_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_code TEXT NOT NULL REFERENCES partners(code),
            material_code TEXT NOT NULL REFERENCES materials(code),
            warehouse_code TEXT NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            status TEXT NOT NULL DEFAULT 'allocated',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS outbound_allocations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL REFERENCES outbound_orders(id),
            inventory_id INTEGER NOT NULL REFERENCES inventory(id),
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            lot_no TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            location_code TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS agv_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL REFERENCES outbound_orders(id),
            source_location TEXT NOT NULL,
            target_location TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'created',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS audit_trail (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            reason TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()


def reset_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DELETE FROM audit_trail;
        DELETE FROM agv_tasks;
        DELETE FROM outbound_allocations;
        DELETE FROM outbound_orders;
        DELETE FROM serial_inventory;
        DELETE FROM inventory;
        DELETE FROM partners;
        DELETE FROM materials;
        DELETE FROM sqlite_sequence WHERE name IN (
            'inventory', 'serial_inventory', 'outbound_orders', 'outbound_allocations', 'agv_tasks', 'audit_trail'
        );
        """
    )
    conn.commit()
