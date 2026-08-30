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
    if (!res.ok) throw new Error(data.detail || "Failed");
    return data;
  }

  const money = (n) => "₹" + (Math.round(n * 100) / 100).toLocaleString("en-IN");

  function toast(msg, ms = 4000) {
    const el = document.createElement("div");
    el.className = "k-toast";
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), ms);
  }

  function timeSince(dateStr) {
    if (!dateStr) return "";
    const diff = (Date.now() - new Date(dateStr).getTime()) / 1000;
    if (diff < 60) return "just now";
    if (diff < 3600) return Math.floor(diff / 60) + " min ago";
    return Math.floor(diff / 3600) + " hr ago";
  }

  // Same alert as the admin page, but held longer + a bigger toast, since this
  // screen is meant to be the only thing Mom is watching.
  function alertNewOrder(n) {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      [0, 0.22, 0.44, 0.9, 1.12, 1.34].forEach((delay, i) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain); gain.connect(ctx.destination);
        osc.type = "sine";
        osc.frequency.value = i % 3 === 2 ? 988 : 784;
        gain.gain.setValueAtTime(0.0001, ctx.currentTime + delay);
        gain.gain.exponentialRampToValueAtTime(0.28, ctx.currentTime + delay + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + delay + 0.26);
        osc.start(ctx.currentTime + delay);
        osc.stop(ctx.currentTime + delay + 0.3);
      });
    } catch (e) { /* audio unavailable */ }
    toast(n === 1 ? "🔔 New order!" : `🔔 ${n} new orders!`, 6000);
    document.title = `(${n}) New order · Kitchen`;
    setTimeout(() => { document.title = "Kitchen · Tulsi Foods"; }, 10000);
  }

  const STAGE_ORDER = { new: 0, preparing: 1, ready: 2, out_for_delivery: 3 };
  let seenOrderIds = new Set();

  function renderCard(o) {
    const isDelivery = o.order_type === "delivery";
    const phone = o.customer_phone || "";
    const items = o.items.map(i => `${i.qty} × ${i.name}`).join("<br>");

    let addressHTML = "";
    if (isDelivery) {
      addressHTML = `<div class="k-address">${o.delivery_address || ""}${phone ? ` · <a href="tel:${phone}">${phone}</a>` : ""}</div>`;
    }

    let payHTML = "";
    if (o.payment_method === "cod") {
      payHTML = `<div class="k-pay k-cod">💰 Collect ${money(o.total)} cash</div>`;
    } else if (o.payment_method === "upi") {
      payHTML = `<div class="k-pay k-upi">📱 UPI — confirm ${money(o.total)} received</div>`;
    }

    let actionsHTML = "";
    let statusLineHTML = "";
    if (o.status === "new") {
      actionsHTML = `<button class="k-btn" data-action="advance" data-id="${o.id}" data-next="preparing">🍳 Start Cooking</button>`;
    } else if (o.status === "preparing") {
      actionsHTML = `<button class="k-btn" data-action="advance" data-id="${o.id}" data-next="ready">✅ Food Ready</button>`;
    } else if (o.status === "ready" && isDelivery) {
      actionsHTML = `<button class="k-btn" data-action="dispatch" data-id="${o.id}">🛵 Book Rider</button>
        <button class="k-sub-action" data-action="advance" data-id="${o.id}" data-next="out_for_delivery">Delivering it myself instead</button>`;
    } else if (o.status === "ready" && !isDelivery) {
      actionsHTML = `<button class="k-btn" data-action="advance" data-id="${o.id}" data-next="delivered">🥡 Handed to Customer</button>`;
    } else if (o.status === "out_for_delivery") {
      statusLineHTML = `<div class="k-status-line">🛵 Rider on the way</div>
        <button class="k-sub-action" data-action="advance" data-id="${o.id}" data-next="delivered">Mark delivered</button>`;
    }

    const card = document.createElement("div");
    card.className = `k-card k-${o.status}`;
    card.dataset.id = o.id;
    card.innerHTML = `
      <div class="k-top">
        <div>
          <div class="k-name">#${o.id} · ${o.customer_name || "Customer"}</div>
          <div class="k-meta">${isDelivery ? "Delivery" : "Pickup"}${o.created_at ? " · " + timeSince(o.created_at) : ""}</div>
        </div>
      </div>
      <div class="k-items">${items}</div>
      ${o.notes ? `<div class="k-notes">"${o.notes}"</div>` : ""}
      ${addressHTML}
      ${payHTML}
      ${statusLineHTML}
      <div class="k-actions">${actionsHTML}</div>
    `;
    return card;
  }

  async function advance(orderId, nextStatus, btn) {
    if (nextStatus === "delivered" && !confirm("Mark this order delivered?")) return;
    btn.classList.add("k-busy");
    btn.textContent = "Working…";
    try {
      await api(`/api/admin/orders/${orderId}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: nextStatus }),
      });
      load();
    } catch (e) {
      toast(`Failed: ${e.message}`);
      btn.classList.remove("k-busy");
    }
  }

  async function dispatch(orderId, btn) {
    if (!confirm("Book a delivery rider for this order?")) return;
    btn.classList.add("k-busy");
    btn.textContent = "Booking…";
    try {
      const d = await api(`/api/admin/orders/${orderId}/dispatch`, { method: "POST" });
      toast(`Rider booked — ${d.courier_name || "on the way"}`);
      load();
    } catch (e) {
      toast(`Booking failed: ${e.message}`);
      btn.classList.remove("k-busy");
      btn.textContent = "🛵 Book Rider";
    }
  }

  async function load() {
    try {
      const d = await api("/api/admin/today-orders");
      const live = d.orders.filter(o => ["new", "preparing", "ready", "out_for_delivery"].includes(o.status));
      const freshIds = new Set(live.map(o => o.id));
      const isFirstLoad = seenOrderIds.size === 0;
      const newOnes = [...freshIds].filter(id => !seenOrderIds.has(id));
      if (!isFirstLoad && newOnes.length) alertNewOrder(newOnes.length);
      seenOrderIds = freshIds;

      live.sort((a, b) => {
        const stageDiff = STAGE_ORDER[a.status] - STAGE_ORDER[b.status];
        if (stageDiff !== 0) return stageDiff;
        return new Date(a.created_at) - new Date(b.created_at);
      });

      document.getElementById("kh-summary").textContent =
        live.length === 0 ? "All caught up" : `${live.length} order${live.length > 1 ? "s" : ""} to handle`;

      const list = document.getElementById("orders-list");
      const empty = document.getElementById("orders-empty");
      empty.hidden = live.length > 0;
      list.innerHTML = "";
      for (const o of live) list.appendChild(renderCard(o));

      list.querySelectorAll('[data-action="advance"]').forEach(btn => {
        btn.addEventListener("click", () => advance(btn.dataset.id, btn.dataset.next, btn));
      });
      list.querySelectorAll('[data-action="dispatch"]').forEach(btn => {
        btn.addEventListener("click", () => dispatch(btn.dataset.id, btn));
      });
    } catch (e) {
      document.getElementById("kh-summary").textContent = "Couldn't load — retrying…";
    }
  }

  load();
  setInterval(load, 12000);
})();
