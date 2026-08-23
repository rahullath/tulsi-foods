(() => {
  const TOKEN_KEY = "tulsi_admin_token";
  let token = localStorage.getItem(TOKEN_KEY);
  if (!token) {
    token = prompt("Admin token:");
    if (!token) return;
    localStorage.setItem(TOKEN_KEY, token);
  }
  const headers = { "X-Admin-Token": token };

  async function api(url, opts = {}) {
    const res = await fetch(url, { ...opts, headers: { ...headers, ...(opts.headers || {}) } });
    if (res.status === 401) { localStorage.removeItem(TOKEN_KEY); location.reload(); }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Request failed");
    return data;
  }

  const money = (n) => "₹" + (Math.round(n * 100) / 100).toLocaleString("en-IN");

  function toast(msg) {
    const el = document.createElement("div");
    el.className = "toast";
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 2500);
  }

  function timeSince(dateStr) {
    if (!dateStr) return "";
    const diff = (Date.now() - new Date(dateStr).getTime()) / 1000;
    if (diff < 60) return "just now";
    if (diff < 3600) return Math.floor(diff / 60) + " min";
    if (diff < 86400) return Math.floor(diff / 3600) + " hr";
    return Math.floor(diff / 86400) + " d";
  }

  // ---- Tab navigation ----
  const tabs = document.querySelectorAll(".tab");
  const tabContents = document.querySelectorAll(".tab-content");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      tabContents.forEach(tc => tc.classList.remove("active"));
      tab.classList.add("active");
      document.getElementById("tab-" + tab.dataset.tab).classList.add("active");
    });
  });

  // ---- Filter chips ----
  let activeFilter = "live";
  document.querySelectorAll(".ah-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".ah-chip").forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      activeFilter = chip.dataset.filter;
      renderFilteredOrders();
    });
  });

  // ---- Orders ----
  const STATUS_META = {
    new: { badge: "badge-new", label: "NEW", action: "Start cooking", next: "preparing" },
    preparing: { badge: "badge-cooking", label: "COOKING", action: "Food ready", next: "ready" },
    ready: { badge: "badge-ready", label: "READY", action: "Out for delivery", next: "out_for_delivery" },
    out_for_delivery: { badge: "badge-cooking", label: "DISPATCHED", action: "Delivered", next: "delivered" },
    delivered: { badge: "badge-done", label: "DONE", action: null, next: null },
    cancelled: { badge: "badge-cancelled", label: "CANCELLED", action: null, next: null },
  };
  const PROGRESS = { new: 0, preparing: 1, ready: 2, out_for_delivery: 3, delivered: 4 };

  let allOrders = [];

  function renderOrder(o) {
    const meta = STATUS_META[o.status] || STATUS_META.new;
    const isDone = ["delivered", "cancelled"].includes(o.status);
    const items = o.items.map(i => `${i.name} × ${i.qty}`).join(" · ");
    const phone = o.customer_phone || "";
    const addr = o.delivery_address || "";
    const pin = o.delivery_pincode || "";
    const typeLabel = o.order_type === "delivery"
      ? `Delivery · ${pin}${addr ? " · " + addr.slice(0, 20) : ""}` + (o.payment_method ? ` · ${o.payment_method.toUpperCase()}` : "")
      : `Pickup` + (o.payment_method ? ` · ${o.payment_method.toUpperCase()}` : "");

    let progressHTML = "";
    if (!isDone && o.status !== "cancelled") {
      const steps = 5;
      const filled = (PROGRESS[o.status] || 0) + 1;
      progressHTML = `<div class="order-progress">${Array.from({length: steps}, (_, i) =>
        `<div class="progress-bar${i < filled ? " filled" : ""}"></div>`
      ).join("")}</div>`;
    }

    let dispatchHTML = "";
    if (o.status === "ready" && o.order_type === "delivery") {
      dispatchHTML = `<div class="order-dispatch"><span class="dispatch-label">Book a rider</span><span class="dispatch-action" data-id="${o.id}">Book</span></div>`;
    }

    let actionsHTML = "";
    if (meta.action) {
      actionsHTML = `<div class="order-actions">
        <button class="action-primary" data-id="${o.id}" data-next="${meta.next}">${meta.action}</button>
        <button class="action-secondary" data-id="${o.id}" title="More">⋯</button>
      </div>`;
    }

    const card = document.createElement("div");
    card.className = "order-card" + (isDone ? " dimmed" : "");
    card.dataset.status = o.status;
    card.dataset.id = o.id;
    card.innerHTML = `
      <div class="order-top">
        <div class="order-info">
          <div class="order-name">#${o.id} · ${o.customer_name || "Customer"}</div>
          <div class="order-meta">${typeLabel}${o.created_at ? " · " + timeSince(o.created_at) : ""}</div>
        </div>
        <span class="order-badge ${meta.badge}">${meta.label}${!isDone && o.created_at ? " · " + timeSince(o.created_at) : ""}</span>
      </div>
      <div class="order-items">${items}${o.notes ? `<br><span class="order-notes">"${o.notes}"</span>` : ""}</div>
      ${progressHTML}
      ${dispatchHTML}
      ${actionsHTML}
    `;
    return card;
  }

  function renderFilteredOrders() {
    const list = document.getElementById("orders-list");
    const empty = document.getElementById("orders-empty");
    list.innerHTML = "";
    const filtered = allOrders.filter(o => {
      if (activeFilter === "all") return true;
      if (activeFilter === "live") return ["new", "preparing", "ready", "out_for_delivery"].includes(o.status);
      if (activeFilter === "scheduled") return false;
      if (activeFilter === "done") return ["delivered", "cancelled"].includes(o.status);
      return true;
    });
    empty.hidden = filtered.length > 0;
    for (const o of filtered) list.appendChild(renderOrder(o));
    list.querySelectorAll(".action-primary").forEach(btn => {
      btn.addEventListener("click", () => advanceOrder(btn.dataset.id, btn.dataset.next, btn));
    });
    list.querySelectorAll(".dispatch-action").forEach(btn => {
      btn.addEventListener("click", () => dispatchOrder(btn.dataset.id, btn));
    });
  }

  async function dispatchOrder(orderId, btn) {
    btn.textContent = "Booking…";
    btn.style.pointerEvents = "none";
    try {
      const d = await api(`/api/admin/orders/${orderId}/dispatch`, { method: "POST" });
      const kind = d.is_hyperlocal ? "Quick rider" : "STANDARD courier (not Quick)";
      toast(`Order #${orderId} → ${kind} booked: ${d.courier_name || "courier"}`);
      loadOrders();
    } catch (e) {
      toast(`Booking failed: ${e.message}`);
      btn.textContent = "Book";
      btn.style.pointerEvents = "";
    }
  }

  async function loadOrders() {
    try {
      const d = await api("/api/admin/today-orders");
      allOrders = d.orders;
      const live = allOrders.filter(o => ["new", "preparing", "ready", "out_for_delivery"].includes(o.status));
      const done = allOrders.filter(o => ["delivered", "cancelled"].includes(o.status));
      const total = allOrders.reduce((s, o) => s + (o.total || 0), 0);
      const chipLive = document.querySelector('[data-filter="live"]');
      const chipDone = document.querySelector('[data-filter="done"]');
      if (chipLive) chipLive.textContent = `Live · ${live.length}`;
      if (chipDone) chipDone.textContent = `Done · ${done.length}`;
      document.getElementById("day-summary").textContent = `${allOrders.length} orders · ${money(total)}`;
      renderFilteredOrders();
    } catch (e) {
      document.getElementById("orders-empty").textContent = "Failed to load: " + e.message;
      document.getElementById("orders-empty").hidden = false;
    }
  }

  async function advanceOrder(orderId, nextStatus, btn) {
    btn.disabled = true;
    btn.textContent = "Updating…";
    try {
      await api(`/api/admin/orders/${orderId}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: nextStatus }),
      });
      toast(`Order #${orderId} → ${nextStatus}`);
      loadOrders();
    } catch (e) {
      btn.textContent = "Failed: " + e.message;
      btn.disabled = false;
    }
  }

  // ---- Menu ----
  async function loadMenu() {
    try {
      const d = await api("/api/admin/availability");
      const on = new Set(d.available_ids);
      const all = document.querySelectorAll(".toggle input");
      let onCount = 0;
      all.forEach(inp => {
        inp.checked = on.has(inp.dataset.id);
        if (inp.checked) onCount++;
      });
      document.getElementById("menu-count").textContent = `${onCount} of ${all.length} items on`;
      if (d.last_day) document.getElementById("menu-count").textContent += ` · copied from ${d.last_day}`;
    } catch (e) {
      document.getElementById("menu-count").textContent = "Failed to load menu";
    }
  }

  let saveTimer = null;
  document.addEventListener("change", (e) => {
    if (!e.target.classList.contains("avail-check")) return;
    clearTimeout(saveTimer);
    saveTimer = setTimeout(saveMenu, 400);
  });

  async function saveMenu() {
    const checks = document.querySelectorAll(".avail-check");
    try {
      await api("/api/admin/availability", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          available_ids: [...checks].filter(c => c.checked).map(c => c.dataset.id),
          unavailable_ids: [...checks].filter(c => !c.checked).map(c => c.dataset.id),
        }),
      });
      toast("Menu saved ✓");
      loadMenu();
    } catch (e) {
      toast("Save failed: " + e.message);
    }
  }

  document.getElementById("repeat-yesterday").addEventListener("click", async () => {
    try {
      await api("/api/admin/availability/repeat-yesterday", { method: "POST" });
      toast("Copied from yesterday ✓");
      loadMenu();
    } catch (e) {
      toast("Failed: " + e.message);
    }
  });

  document.getElementById("all-on").addEventListener("click", async () => {
    const checks = document.querySelectorAll(".avail-check");
    checks.forEach(c => { c.checked = true; });
    await saveMenu();
    toast("All items on ✓");
  });

  // ---- Chats ----
  async function loadConvos() {
    try {
      const d = await api("/api/admin/conversations");
      const list = document.getElementById("convos-list");
      const empty = document.getElementById("convos-empty");
      list.innerHTML = "";
      empty.hidden = d.conversations.length > 0;
      for (const c of d.conversations) {
        const card = document.createElement("div");
        card.className = "convo-card";
        card.innerHTML = `
          <div class="convo-info">
            <div class="convo-name">${c.name || c.wa_id}</div>
            <div class="convo-detail">${c.wa_id}${c.updated_at ? " · " + c.updated_at : ""}</div>
          </div>
          <button class="convo-toggle${c.human ? " human" : ""}" data-wa="${c.wa_id}" data-human="${c.human ? 1 : 0}">
            ${c.human ? "You" : "Bot"}
          </button>
        `;
        list.appendChild(card);
      }
      list.querySelectorAll(".convo-toggle").forEach(btn => {
        btn.addEventListener("click", async () => {
          const next = !(btn.dataset.human === "1");
          btn.disabled = true;
          try {
            await api(`/api/admin/conversations/${encodeURIComponent(btn.dataset.wa)}/human`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ human: next }),
            });
            btn.dataset.human = next ? "1" : "0";
            btn.textContent = next ? "You" : "Bot";
            btn.classList.toggle("human", next);
          } finally { btn.disabled = false; }
        });
      });
    } catch (e) {
      document.getElementById("convos-empty").hidden = false;
    }
  }

  // ---- Day stats ----
  async function loadDayStats() {
    try {
      const d = await api("/api/admin/today-orders");
      const orders = d.orders;
      const total = orders.reduce((s, o) => s + (o.total || 0), 0);
      const delivered = orders.filter(o => o.status === "delivered");
      const avg = delivered.length ? money(total / delivered.length) : "—";
      const delivery = orders.filter(o => o.order_type === "delivery");
      const pickup = orders.filter(o => o.order_type === "pickup");
      document.getElementById("day-stats").innerHTML = `
        <div>Total orders: <span class="day-stat-val">${orders.length}</span></div>
        <div>Revenue: <span class="day-stat-val">${money(total)}</span></div>
        <div>Avg order: <span class="day-stat-val">${avg}</span></div>
        <div>Delivered: <span class="day-stat-val">${delivered.length}</span></div>
        <div>Delivery: <span class="day-stat-val">${delivery.length}</span> · Pickup: <span class="day-stat-val">${pickup.length}</span></div>
      `;
    } catch (e) {
      document.getElementById("day-stats").textContent = "Failed to load stats";
    }
  }

  // ---- Init ----
  loadOrders();
  loadMenu().catch(() => {});
  loadConvos().catch(() => {});
  loadDayStats().catch(() => {});
  setInterval(loadOrders, 30000);
})();
