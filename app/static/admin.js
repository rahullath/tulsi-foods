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

  function formatScheduled(dateStr) {
    return "FOR " + new Date(dateStr).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" }).toUpperCase();
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

    let flagHTML = "";
    if (o.address_flagged && !isDone) {
      const waLink = phone ? `https://wa.me/${phone.replace(/\D/g, "")}` : null;
      flagHTML = `<div class="order-flag">
        <div class="order-flag-title">Address needs checking</div>
        <div class="order-flag-reason">${o.address_flag_reason || ""}</div>
        ${waLink ? `<a class="order-flag-action" href="${waLink}" target="_blank" rel="noopener">Ask on WhatsApp</a>` : ""}
      </div>`;
    }

    let quickHTML = "";
    if (o.order_type === "delivery" && !isDone) {
      const waLink = phone ? `https://wa.me/${phone.replace(/\D/g, "")}` : null;
      const mapsQuery = (o.delivery_lat && o.delivery_lng)
        ? `${o.delivery_lat},${o.delivery_lng}`
        : encodeURIComponent(addr || "");
      const mapsLink = mapsQuery ? `https://www.google.com/maps/search/?api=1&query=${mapsQuery}` : null;
      quickHTML = `<div class="order-quick">
        ${phone ? `<a class="quick-btn" href="tel:${phone}">Call</a>` : ""}
        ${waLink ? `<a class="quick-btn" href="${waLink}" target="_blank" rel="noopener">WhatsApp</a>` : ""}
        ${mapsLink ? `<a class="quick-btn quick-btn-muted" href="${mapsLink}" target="_blank" rel="noopener">Open in Maps</a>` : ""}
      </div>`;
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
        <span class="order-badge ${meta.badge}">${meta.label}${!isDone && o.scheduled_at ? " · " + formatScheduled(o.scheduled_at) : (!isDone && o.created_at ? " · " + timeSince(o.created_at) : "")}</span>
      </div>
      <div class="order-items">${items}${o.notes ? `<br><span class="order-notes">"${o.notes}"</span>` : ""}</div>
      ${flagHTML}
      ${quickHTML}
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
      if (activeFilter === "scheduled") return !!o.scheduled_at && !["delivered", "cancelled"].includes(o.status);
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
      toast(`Order #${orderId} → rider booked (${d.courier_name || "courier"})`);
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
      const scheduled = allOrders.filter(o => o.scheduled_at && !["delivered", "cancelled"].includes(o.status));
      const total = allOrders.reduce((s, o) => s + (o.total || 0), 0);
      const chipLive = document.querySelector('[data-filter="live"]');
      const chipScheduled = document.querySelector('[data-filter="scheduled"]');
      const chipDone = document.querySelector('[data-filter="done"]');
      if (chipLive) chipLive.textContent = `Live · ${live.length}`;
      if (chipScheduled) chipScheduled.textContent = `Scheduled · ${scheduled.length}`;
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

  // ---- Reviews ----
  const SOURCE_LABELS = {
    google: "Google", swiggy: "Swiggy", zomato: "Zomato", instagram: "Instagram",
    facebook: "Facebook", whatsapp: "WhatsApp", in_person: "Physical / in-person",
  };

  function renderReview(r) {
    const card = document.createElement("div");
    card.className = "review-card";
    const stars = r.rating ? "★".repeat(r.rating) + "☆".repeat(5 - r.rating) : "";
    card.innerHTML = `
      <div class="review-top">
        <div>
          <span class="review-source">${SOURCE_LABELS[r.source] || r.source}</span>
          <div class="review-quote">"${r.quote}"</div>
          <div class="review-meta">${r.author_name || "Anonymous"}${stars ? " · " + stars : ""}${r.proof_url ? ` · <a href="${r.proof_url}" target="_blank" rel="noopener">proof</a>` : ""}</div>
        </div>
        <div class="review-actions">
          <label class="toggle" title="Feature on site">
            <input type="checkbox" class="review-feature" data-id="${r.id}" ${r.featured ? "checked" : ""}>
            <span class="slider"></span>
          </label>
          <button type="button" class="review-delete" data-id="${r.id}">Delete</button>
        </div>
      </div>
    `;
    return card;
  }

  async function loadReviews() {
    try {
      const d = await api("/api/admin/reviews");
      const list = document.getElementById("reviews-list");
      const empty = document.getElementById("reviews-empty");
      list.innerHTML = "";
      empty.hidden = d.reviews.length > 0;
      for (const r of d.reviews) list.appendChild(renderReview(r));
      list.querySelectorAll(".review-feature").forEach(inp => {
        inp.addEventListener("change", async () => {
          try {
            await api(`/api/admin/reviews/${inp.dataset.id}/feature`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ featured: inp.checked }),
            });
            toast(inp.checked ? "Featured on site ✓" : "Removed from site");
          } catch (e) { toast("Failed: " + e.message); inp.checked = !inp.checked; }
        });
      });
      list.querySelectorAll(".review-delete").forEach(btn => {
        btn.addEventListener("click", async () => {
          if (!confirm("Delete this review?")) return;
          try {
            await api(`/api/admin/reviews/${btn.dataset.id}`, { method: "DELETE" });
            loadReviews();
          } catch (e) { toast("Failed: " + e.message); }
        });
      });
    } catch (e) {
      document.getElementById("reviews-empty").textContent = "Failed to load: " + e.message;
      document.getElementById("reviews-empty").hidden = false;
    }
  }

  document.getElementById("review-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      await api("/api/admin/reviews", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source: fd.get("source"),
          quote: fd.get("quote"),
          author_name: fd.get("author_name") || null,
          rating: fd.get("rating") ? Number(fd.get("rating")) : null,
          proof_url: fd.get("proof_url") || null,
        }),
      });
      e.target.reset();
      toast("Review added ✓");
      loadReviews();
    } catch (e) { toast("Failed: " + e.message); }
  });

  async function loadPlatformStats() {
    try {
      const d = await api("/api/admin/platform-stats");
      const s = d.stats || {};
      const form = document.getElementById("platform-stats-form");
      if (s.swiggy) {
        form.querySelector('[name=swiggy_rating]').value = s.swiggy.rating ?? "";
        form.querySelector('[name=swiggy_count]').value = s.swiggy.review_count ?? "";
      }
      if (s.zomato) {
        form.querySelector('[name=zomato_rating]').value = s.zomato.rating ?? "";
        form.querySelector('[name=zomato_count]').value = s.zomato.review_count ?? "";
      }
      const googleDisplay = document.getElementById("google-stats-display");
      googleDisplay.textContent = s.google
        ? `Google: ${s.google.rating}★ (${s.google.review_count} reviews) · updated ${s.google.updated_at}`
        : "Google: not configured yet (needs GOOGLE_PLACES_API_KEY + GOOGLE_PLACE_ID)";
    } catch (e) { /* non-fatal — form just stays blank */ }
  }

  document.getElementById("platform-stats-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      const swiggyRating = fd.get("swiggy_rating"), swiggyCount = fd.get("swiggy_count");
      const zomatoRating = fd.get("zomato_rating"), zomatoCount = fd.get("zomato_count");
      if (swiggyRating || swiggyCount) {
        await api("/api/admin/platform-stats", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ platform: "swiggy", rating: swiggyRating ? Number(swiggyRating) : null, review_count: swiggyCount ? Number(swiggyCount) : null }),
        });
      }
      if (zomatoRating || zomatoCount) {
        await api("/api/admin/platform-stats", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ platform: "zomato", rating: zomatoRating ? Number(zomatoRating) : null, review_count: zomatoCount ? Number(zomatoCount) : null }),
        });
      }
      toast("Numbers saved ✓");
      loadPlatformStats();
    } catch (e) { toast("Failed: " + e.message); }
  });

  // ---- Init ----
  loadOrders();
  loadMenu().catch(() => {});
  loadConvos().catch(() => {});
  loadDayStats().catch(() => {});
  loadReviews().catch(() => {});
  loadPlatformStats().catch(() => {});
  setInterval(loadOrders, 30000);
})();
