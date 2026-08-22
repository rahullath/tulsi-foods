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
    pincode    TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS orders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id     INTEGER REFERENCES customers(id),
    status          TEXT NOT NULL DEFAULT 'new',
    order_type      TEXT NOT NULL DEFAULT 'delivery',
    subtotal        REAL NOT NULL,
    delivery_fee    REAL NOT NULL DEFAULT 0,
    total           REAL NOT NULL,
    payment_method  TEXT NOT NULL DEFAULT 'cod',
    paid            INTEGER NOT NULL DEFAULT 0,
    instructions    TEXT,
    scheduled_at    TEXT,
    delivery_address TEXT,
    delivery_pincode TEXT,
    sr_order_id     INTEGER,
    sr_awb          TEXT,
    sr_courier      TEXT,
    sr_tracking_url TEXT,
    dispatched_at   TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
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
CREATE TABLE IF NOT EXISTS daily_specials (
    date      TEXT PRIMARY KEY,
    item_name TEXT NOT NULL,
    price     REAL NOT NULL
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
    _migrate(conn)
    conn.commit()
    conn.close()


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns that may not exist in older databases."""
    def _has_col(table: str, col: str) -> bool:
        return col in [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]

    if not _has_col("customers", "pincode"):
        conn.execute("ALTER TABLE customers ADD COLUMN pincode TEXT")
    if not _has_col("orders", "delivery_address"):
        conn.execute("ALTER TABLE orders ADD COLUMN delivery_address TEXT")
    if not _has_col("orders", "delivery_pincode"):
        conn.execute("ALTER TABLE orders ADD COLUMN delivery_pincode TEXT")
    if not _has_col("orders", "sr_order_id"):
        conn.execute("ALTER TABLE orders ADD COLUMN sr_order_id INTEGER")
    if not _has_col("orders", "sr_awb"):
        conn.execute("ALTER TABLE orders ADD COLUMN sr_awb TEXT")
    if not _has_col("orders", "sr_courier"):
        conn.execute("ALTER TABLE orders ADD COLUMN sr_courier TEXT")
    if not _has_col("orders", "sr_tracking_url"):
        conn.execute("ALTER TABLE orders ADD COLUMN sr_tracking_url TEXT")
    if not _has_col("orders", "dispatched_at"):
        conn.execute("ALTER TABLE orders ADD COLUMN dispatched_at TEXT")
    # daily_specials table (may not exist in older databases)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS daily_specials ("
        "    date      TEXT PRIMARY KEY,"
        "    item_name TEXT NOT NULL,"
        "    price     REAL NOT NULL"
        ")"
    )


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

def upsert_customer(phone: str, name: str, address: str | None = None,
                     pincode: str | None = None) -> int:
    conn = get_conn()
    conn.execute(
        "INSERT INTO customers(phone, name, address, pincode) VALUES(?,?,?,?) "
        "ON CONFLICT(phone) DO UPDATE SET name=excluded.name, "
        "address=COALESCE(excluded.address, customers.address), "
        "pincode=COALESCE(excluded.pincode, customers.pincode)",
        (phone, name, address, pincode),
    )
    conn.commit()
    cid = conn.execute("SELECT id FROM customers WHERE phone=?", (phone,)).fetchone()["id"]
    conn.close()
    return cid


def get_customer(phone: str) -> dict | None:
    """Get customer record by phone number."""
    conn = get_conn()
    row = conn.execute(
        "SELECT id, phone, name, address, pincode FROM customers WHERE phone=?",
        (phone,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_order(customer_id: int, order_type: str, subtotal: float,
                 delivery_fee: float, total: float, payment_method: str,
                 instructions: str | None, items: list[dict],
                 delivery_address: str | None = None,
                 delivery_pincode: str | None = None) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO orders(customer_id, status, order_type, subtotal, delivery_fee, "
        "total, payment_method, instructions, delivery_address, delivery_pincode) "
        "VALUES(?,?,?,?,?,?,?,?,?,?)",
        (customer_id, "new", order_type, subtotal, delivery_fee, total,
         payment_method, instructions, delivery_address, delivery_pincode),
    )
    oid = cur.lastrowid
    conn.executemany(
        "INSERT INTO order_items(order_id, item_id, name, price, qty) VALUES(?,?,?,?,?)",
        [(oid, i["item_id"], i["name"], i["price"], i["qty"]) for i in items],
    )
    conn.commit()
    conn.close()
    return oid


def update_order_dispatch(order_id: int, sr_order_id: int, awb: str,
                          courier: str, tracking_url: str) -> None:
    """Store Shiprocket dispatch details and mark as out_for_delivery."""
    from datetime import datetime
    conn = get_conn()
    conn.execute(
        "UPDATE orders SET status='out_for_delivery', sr_order_id=?, sr_awb=?, "
        "sr_courier=?, sr_tracking_url=?, dispatched_at=? WHERE id=?",
        (sr_order_id, awb, courier, tracking_url, datetime.utcnow().isoformat(), order_id),
    )
    conn.commit()
    conn.close()


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


def customer_orders(phone: str, limit: int = 5) -> list[dict]:
    """Get recent orders for a customer (for reorder)."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT o.id, o.status, o.total, o.order_type, o.created_at "
        "FROM orders o LEFT JOIN customers c ON c.id=o.customer_id "
        "WHERE c.phone=? AND o.status != 'cancelled' "
        "ORDER BY o.id DESC LIMIT ?",
        (phone, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def today_orders() -> list[dict]:
    """Today's orders with full details for admin dashboard."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT o.*, c.name AS customer_name, c.phone AS customer_phone "
        "FROM orders o LEFT JOIN customers c ON c.id=o.customer_id "
        "WHERE date(o.created_at) = date('now') "
        "ORDER BY o.id DESC"
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        ic = get_conn()
        items = ic.execute(
            "SELECT item_id, name, price, qty FROM order_items WHERE order_id=?",
            (d["id"],),
        ).fetchall()
        ic.close()
        d["items"] = [dict(i) for i in items]
        result.append(d)
    conn.close()
    return result


def seeded() -> None:
    """Seed menu ids into availability so 'today's menu' = full menu until toggled."""
    from .menu import load_menu
    menu = load_menu()
    today = date.today().isoformat()
    ids = [m["id"] for m in menu]
    set_availability(today, ids, [])


# ---- daily specials ----

def get_special(day: str | None = None) -> dict | None:
    day = day or date.today().isoformat()
    conn = get_conn()
    row = conn.execute(
        "SELECT item_name, price FROM daily_specials WHERE date=?", (day,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def set_special(day: str, item_name: str, price: float) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO daily_specials(date, item_name, price) VALUES(?,?,?) "
        "ON CONFLICT(date) DO UPDATE SET item_name=excluded.item_name, price=excluded.price",
        (day, item_name, price),
    )
    conn.commit()
    conn.close()


def clear_special(day: str | None = None) -> None:
    day = day or date.today().isoformat()
    conn = get_conn()
    conn.execute("DELETE FROM daily_specials WHERE date=?", (day,))
    conn.commit()
    conn.close()
