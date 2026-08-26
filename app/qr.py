"""Printed-QR redirect.

The flyer QR encodes https://tulsifoods.app/f — a permanent short URL whose
destination lives here, so a printed flyer can be repointed (menu, a campaign
page, WhatsApp) without reprinting anything. ?c= tags the print run/area so we
can tell which drop actually converted.
"""
import os
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from . import db

router = APIRouter()

# Where the printed QR currently lands. Change the env var, not the flyer.
QR_TARGET = os.getenv("QR_TARGET", "https://tulsifoods.app/menu")

SCAN_SCHEMA = """
CREATE TABLE IF NOT EXISTS qr_scans (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign   TEXT,
    target     TEXT,
    user_agent TEXT,
    referer    TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


def init_qr() -> None:
    conn = db.get_conn()
    conn.executescript(SCAN_SCHEMA)
    conn.commit()
    conn.close()


def _log_scan(campaign: str | None, target: str, request: Request) -> None:
    try:
        conn = db.get_conn()
        conn.execute(
            "INSERT INTO qr_scans(campaign, target, user_agent, referer) VALUES(?,?,?,?)",
            (campaign, target, request.headers.get("user-agent", ""),
             request.headers.get("referer", "")),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass  # never block the redirect on logging


@router.get("/f")
def flyer_redirect(request: Request, c: str | None = None):
    _log_scan(c, QR_TARGET, request)
    # 302, not 301: a permanent redirect gets cached by the phone's browser and
    # we lose the ability to repoint the printed code.
    return RedirectResponse(QR_TARGET, status_code=302)


@router.get("/api/admin/qr-scans")
def qr_scans(limit: int = 200):
    conn = db.get_conn()
    rows = conn.execute(
        "SELECT campaign, COUNT(*) AS scans, MAX(created_at) AS last_scan "
        "FROM qr_scans GROUP BY campaign ORDER BY scans DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return {"by_campaign": [dict(r) for r in rows]}
