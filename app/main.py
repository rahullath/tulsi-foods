from datetime import date

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from . import db, menu, orders
from .config import ADMIN_TOKEN, DELIVERY_ZONES

app = FastAPI(title="Tulsi Foods Direct Ordering", version="0.1.0")

from .webhooks import router as webhook_router

app.include_router(webhook_router)

templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# ---- pages ----

@app.get("/", response_class=HTMLResponse)
def index_page(request: Request):
    return templates.TemplateResponse(
        request, "index.html", {"groups": menu.grouped(), "zones": DELIVERY_ZONES}
    )


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    return templates.TemplateResponse(
        request, "admin.html", {"groups": menu.grouped()}
    )


@app.get("/privacy-policy", response_class=HTMLResponse)
def privacy_page(request: Request):
    return templates.TemplateResponse(request, "privacy.html", {})


# ---- menu API ----

@app.get("/api/menu")
def api_menu(day: str | None = None):
    return {"date": menu.today(day), "groups": menu.grouped(day)}


@app.get("/api/delivery")
def api_delivery(km: float, subtotal: float = 0.0):
    q = orders.delivery_fee(km, subtotal)
    if not q:
        return {"zone": "outside", "fee": None, "min_order": None}
    return {"zone": q["zone"], "fee": q["fee"], "min_order": q["min_order"]}


# ---- availability (admin) ----

def _check_admin(token: str | None):
    if not token or token != ADMIN_TOKEN:
        raise HTTPException(401, "Invalid admin token")


class AvailabilityIn(BaseModel):
    available_ids: list[str] = Field(default_factory=list)
    unavailable_ids: list[str] = Field(default_factory=list)


@app.get("/api/admin/availability")
def admin_availability(day: str | None = None, x_admin_token: str | None = Header(None)):
    _check_admin(x_admin_token)
    day = menu.today(day)
    available = db.get_available_ids(day)
    return {"date": day, "available_ids": sorted(available), "last_day": db.last_available_day()}


@app.post("/api/admin/availability")
def admin_set_availability(body: AvailabilityIn, day: str | None = None,
                           x_admin_token: str | None = Header(None)):
    _check_admin(x_admin_token)
    day = menu.today(day)
    db.set_availability(day, body.available_ids, body.unavailable_ids)
    return {"date": day, "ok": True}


@app.post("/api/admin/availability/repeat-yesterday")
def admin_repeat_yesterday(x_admin_token: str | None = Header(None)):
    _check_admin(x_admin_token)
    last = db.last_available_day()
    if not last:
        raise HTTPException(400, "No previously saved day to copy")
    today = date.today().isoformat()
    n = db.copy_availability(last, today)
    return {"ok": True, "copied_from": last, "copied_items": n}


# ---- WhatsApp conversations (admin) ----

class HumanIn(BaseModel):
    human: bool


@app.get("/api/admin/conversations")
def admin_conversations(x_admin_token: str | None = Header(None)):
    _check_admin(x_admin_token)
    from .whatsapp import sessions as wa_sessions
    return {"conversations": wa_sessions.all_sessions()}


@app.post("/api/admin/conversations/{wa_id}/human")
def admin_conversation_human(wa_id: str, body: HumanIn,
                             x_admin_token: str | None = Header(None)):
    _check_admin(x_admin_token)
    from .whatsapp import sessions as wa_sessions
    wa_sessions.set_human(wa_id, body.human)
    return {"wa_id": wa_id, "human": body.human, "ok": True}


# ---- orders ----

class OrderItemIn(BaseModel):
    item_id: str
    qty: float = Field(gt=0)


class OrderIn(BaseModel):
    phone: str
    name: str
    address: str | None = None
    order_type: str = "delivery"  # delivery | pickup
    km: float | None = None
    payment_method: str = "cod"   # cod | upi
    instructions: str | None = None
    items: list[OrderItemIn]


@app.post("/api/orders")
def create_order(order: OrderIn):
    try:
        result = orders.create_order(
            phone=order.phone, name=order.name, address=order.address,
            order_type=order.order_type, km=order.km,
            payment_method=order.payment_method, instructions=order.instructions,
            items=[{"item_id": it.item_id, "qty": it.qty} for it in order.items],
        )
        return result
    except orders.OrderError as e:
        raise HTTPException(e.status, e.message)


@app.get("/api/orders/{order_id}")
def get_order(order_id: int):
    o = db.get_order(order_id)
    if not o:
        raise HTTPException(404, "Order not found")
    return o


@app.get("/api/orders")
def list_orders(limit: int = 20):
    return {"orders": db.recent_orders(limit)}


@app.on_event("startup")
def on_startup():
    db.init_db()
    db.seeded()
    from .whatsapp import sessions as wa_sessions
    wa_sessions.init_sessions()
