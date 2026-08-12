"""SQLite persistence: customers, orders, order_items, availability.

Availability is keyed by (date, item_id) with available=1/0.
"Repeat yesterday" copies the most recent saved day.
"""
import json
import sqlite3
from datetime import date
from pathlib import Path

from .config import DB_FILE

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    phone      TEXT UNIQUE,
    name       TEXT,
    address    TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER REFERENCES customers(id),
    status      TEXT NOT NULL DEFAULT 'new',
    order_type  TEXT NOT NULL DEFAULT 'delivery',
    subtotal    REAL NOT NULL,
    delivery_fee REAL NOT NULL DEFAULT 0,
    total       REAL NOT NULL,
    payment_method TEXT NOT NULL DEFAULT 'cod',
    paid        INTEGER NOT NULL DEFAULT 0,
    instructions TEXT,
    scheduled_at TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS order_items (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER REFERENCES orders(id),
    item_id TEXT,
    name    TEXT,
    price   REAL,
    qty     REAL
);
CREATE TABLE IF NOT EXISTS availability (
    date      TEXT NOT NULL,
    item_id   TEXT NOT NULL,
    available INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (date, item_id)
);
"""


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    Path(DB_FILE).parent.mkdir(parents=True, exist_ok=True)
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


# ---- availability ----

def get_available_ids(day: str) -> set[str]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT item_id, available FROM availability WHERE date=?", (day,)
    ).fetchall()
    conn.close()
    return {r["item_id"] for r in rows if r["available"] == 1}


def last_available_day() -> str | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT MAX(date) AS d FROM availability WHERE date < date('now')"
    ).fetchone()
    conn.close()
    return row["d"] if row and row["d"] else None


def set_availability(day: str, available_ids: list[str], unavailable_ids: list[str]) -> None:
    conn = get_conn()
    for item_id in available_ids:
        conn.execute(
            "INSERT INTO availability(date, item_id, available) VALUES(?,?,1) "
            "ON CONFLICT(date, item_id) DO UPDATE SET available=1",
            (day, item_id),
        )
    for item_id in unavailable_ids:
        conn.execute(
            "INSERT INTO availability(date, item_id, available) VALUES(?,?,0) "
            "ON CONFLICT(date, item_id) DO UPDATE SET available=0",
            (day, item_id),
        )
    conn.commit()
    conn.close()


def copy_availability(from_day: str, to_day: str) -> int:
    """Copy a saved day's availability to another day. Returns item count copied."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT item_id, available FROM availability WHERE date=?", (from_day,)
    ).fetchall()
    for r in rows:
        conn.execute(
            "INSERT INTO availability(date, item_id, available) VALUES(?,?,?) "
            "ON CONFLICT(date, item_id) DO UPDATE SET available=excluded.available",
            (to_day, r["item_id"], r["available"]),
        )
    conn.commit()
    conn.close()
    return len(rows)


# ---- customers & orders ----

def upsert_customer(phone: str, name: str, address: str | None = None) -> int:
    conn = get_conn()
    conn.execute(
        "INSERT INTO customers(phone, name, address) VALUES(?,?,?) "
        "ON CONFLICT(phone) DO UPDATE SET name=excluded.name, "
        "address=COALESCE(excluded.address, customers.address)",
        (phone, name, address),
    )
    conn.commit()
    cid = conn.execute("SELECT id FROM customers WHERE phone=?", (phone,)).fetchone()["id"]
    conn.close()
    return cid


def create_order(customer_id: int, order_type: str, subtotal: float,
                 delivery_fee: float, total: float, payment_method: str,
                 instructions: str | None, items: list[dict]) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO orders(customer_id, status, order_type, subtotal, delivery_fee, "
        "total, payment_method, instructions) VALUES(?,?,?,?,?,?,?,?)",
        (customer_id, "new", order_type, subtotal, delivery_fee, total,
         payment_method, instructions),
    )
    oid = cur.lastrowid
    conn.executemany(
        "INSERT INTO order_items(order_id, item_id, name, price, qty) VALUES(?,?,?,?,?)",
        [(oid, i["item_id"], i["name"], i["price"], i["qty"]) for i in items],
    )
    conn.commit()
    conn.close()
    return oid


def get_order(order_id: int) -> dict | None:
    conn = get_conn()
    o = conn.execute(
        "SELECT o.*, c.name AS customer_name, c.phone AS customer_phone, "
        "       c.address AS customer_address "
        "FROM orders o LEFT JOIN customers c ON c.id=o.customer_id "
        "WHERE o.id=?",
        (order_id,),
    ).fetchone()
    if not o:
        conn.close()
        return None
    items = conn.execute(
        "SELECT item_id, name, price, qty FROM order_items WHERE order_id=?",
        (order_id,),
    ).fetchall()
    conn.close()
    d = dict(o)
    d["items"] = [dict(i) for i in items]
    return d


def update_order_status(order_id: int, status: str) -> None:
    conn = get_conn()
    conn.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    conn.commit()
    conn.close()


def recent_orders(limit: int = 20) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT o.id, o.status, o.order_type, o.total, o.payment_method, o.created_at, "
        "       c.name, c.phone "
        "FROM orders o LEFT JOIN customers c ON c.id=o.customer_id "
        "ORDER BY o.id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def seeded() -> None:
    """Seed menu ids into availability so 'today's menu' = full menu until toggled."""
    from .menu import load_menu
    menu = load_menu()
    today = date.today().isoformat()
    ids = [m["id"] for m in menu]
    set_availability(today, ids, [])
