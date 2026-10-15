// Tulsi Kitchen: Mom's order screen. One card per order with the bill split,
// everything needed to book Porter, and one big button for the next step.
// Every button that changes an order also messages the customer on WhatsApp.
(function () {
  const TOKEN_KEY = "tulsi_admin_token";
  const SOUND_KEY = "tulsi_kitchen_sound";
  const app = document.getElementById("app");
  let token = null, data = null, tab = "now", seen = null, soundOn = false, audio = null;
  const drafts = {};  // per-order Porter link/fare typed but not yet sent
  // /kitchen/o/46 (the Open order button on Mom's WhatsApp alert) jumps to #46.
  let focusId = +((/^\/kitchen\/o\/(\d+)/.exec(location.pathname) || [])[1]) || null;

  try { token = localStorage.getItem(TOKEN_KEY); soundOn = localStorage.getItem(SOUND_KEY) === "1"; } catch (_) {}

  // ---------- helpers
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const num = (v) => +v || 0;
  const rs = (v) => { const n = Math.round(num(v) * 100) / 100; return "₹" + (Number.isInteger(n) ? n : n.toFixed(2)); };
  const utc = (s) => s ? new Date(s.replace(" ", "T") + (/[zZ]|[+-]\d\d:?\d\d$/.test(s) ? "" : "Z")) : null;
  const time = (d) => d ? d.toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit", timeZone: "Asia/Kolkata" }) : "";
  const day = (d) => d ? d.toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short", timeZone: "Asia/Kolkata" }) : "";
  const istDay = (d) => d ? d.toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" }) : "";
  const ago = (d) => { if (!d) return ""; const m = Math.round((Date.now() - d) / 60000); return m < 1 ? "just now" : m < 60 ? m + " min ago" : Math.floor(m / 60) + " h " + (m % 60) + " min ago"; };
  const phone10 = (p) => String(p || "").replace(/\D/g, "");
  const waNum = (p) => { const d = phone10(p); return d.length === 10 ? "91" + d : d; };
  const prettyPhone = (p) => { const d = phone10(p); return d.length === 10 ? d.slice(0, 5) + " " + d.slice(5) : "+" + d; };
  const splitAddr = (a) => { const m = /\s*\(Landmark:\s*(.*?)\)\s*$/i.exec(a || ""); return m ? [a.slice(0, m.index), m[1]] : [a || "", ""]; };
  const WINDOWS = { lunch: "Lunch (12:00–2:30)", dinner: "Dinner (6:30–9:30)" };

  function toast(msg, ms) {
    const t = document.createElement("div"); t.className = "toast"; t.textContent = msg;
    document.body.appendChild(t); setTimeout(() => t.remove(), ms || 3500);
  }

  async function api(url, opts) {
    opts = opts || {};
    const res = await fetch(url, { ...opts, headers: { "X-Admin-Token": token, "Content-Type": "application/json", ...(opts.headers || {}) } });
    if (res.status === 401) { try { localStorage.removeItem(TOKEN_KEY); } catch (_) {} token = null; renderLogin("That password didn't work. Try again."); throw new Error("auth"); }
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.detail || "Something went wrong. Try again.");
    return body;
  }

  // ---------- sound (phones only allow it after a tap)
  function unlockSound() {
    try { audio = audio || new (window.AudioContext || window.webkitAudioContext)(); audio.resume(); } catch (_) {}
  }
  function ring() {
    if (navigator.vibrate) navigator.vibrate([400, 200, 400, 200, 400]);
    if (!soundOn || !audio) return;
    [0, .22, .44, .9, 1.12, 1.34, 1.8, 2.02, 2.24].forEach((t, i) => {
      const o = audio.createOscillator(), g = audio.createGain();
      o.connect(g); g.connect(audio.destination); o.type = "sine"; o.frequency.value = i % 3 === 2 ? 988 : 784;
      const at = audio.currentTime + t;
      g.gain.setValueAtTime(.0001, at); g.gain.exponentialRampToValueAtTime(.35, at + .02); g.gain.exponentialRampToValueAtTime(.0001, at + .26);
      o.start(at); o.stop(at + .3);
    });
  }

  // ---------- grouping
  const needsMoney = (o) => (o.payment_method === "upi" && !o.paid && o.status !== "cancelled" && o.status !== "delivered") ? 1 : 0;
  const OPEN = ["new", "preparing", "ready", "out_for_delivery"];
  function isLater(o) {
    if (!o.scheduled_at || o.status !== "new") return false;
    return istDay(utc(o.scheduled_at)) > istDay(new Date());
  }
  function groups() {
    const all = (data && data.orders) || [];
    const today = istDay(new Date());
    const now = all.filter((o) => OPEN.includes(o.status) && !isLater(o));
    const later = all.filter((o) => OPEN.includes(o.status) && isLater(o));
    const done = all.filter((o) => !OPEN.includes(o.status) && istDay(utc(o.created_at)) === today);
    const rank = { new: 0, preparing: 1, ready: 2, out_for_delivery: 3 };
    now.sort((a, b) => (needsMoney(b) - needsMoney(a)) || rank[a.status] - rank[b.status] || a.id - b.id);
    later.sort((a, b) => (a.scheduled_at || "").localeCompare(b.scheduled_at || ""));
    return { now, later, done };
  }

  // ---------- views
  function renderLogin(err) {
    app.innerHTML = `<form class="login" id="login">
      <h1>Tulsi Kitchen</h1>
      <div class="hint">Enter the kitchen password once. This phone remembers it.</div>
      <input id="pw" type="password" autocomplete="current-password" placeholder="Kitchen password" required>
      ${err ? `<div class="flag">${esc(err)}</div>` : ""}
      <button class="big" type="submit">Open the kitchen</button>
    </form>`;
    document.getElementById("login").addEventListener("submit", (e) => {
      e.preventDefault();
      token = document.getElementById("pw").value.trim();
      try { localStorage.setItem(TOKEN_KEY, token); } catch (_) {}
      unlockSound(); start();
    });
  }

  function summary(g) {
    const today = istDay(new Date());
    const todays = ((data && data.orders) || []).filter((o) => o.status !== "cancelled" && istDay(utc(o.created_at)) === today);
    const sales = todays.reduce((s, o) => s + num(o.total), 0);
    return `${todays.length} order${todays.length === 1 ? "" : "s"} today · ${rs(Math.round(sales))}` + (g.now.length ? ` · ${g.now.length} open` : "");
  }

  function render() {
    const g = groups();
    const list = g[tab];
    const keepScroll = window.scrollY;
    app.innerHTML = `
      <header class="top">
        <div class="top-row">
          <div><h1>Tulsi Kitchen</h1><div class="sum">${summary(g)}</div></div>
          <button class="sound ${soundOn ? "on" : ""}" id="sound">${soundOn ? "🔔 Sound on" : "🔕 Sound off"}</button>
        </div>
        <nav class="tabs">
          <button data-tab="now" class="${tab === "now" ? "on" : ""}">Now<span class="n">${g.now.length}</span></button>
          <button data-tab="later" class="${tab === "later" ? "on" : ""}">Later<span class="n">${g.later.length}</span></button>
          <button data-tab="done" class="${tab === "done" ? "on" : ""}">Done today<span class="n">${g.done.length}</span></button>
        </nav>
      </header>
      ${g.now.filter(needsMoney).length ? `<button class="banner pay" id="payalert">💰 ${g.now.filter(needsMoney).length} UPI payment${g.now.filter(needsMoney).length > 1 ? "s" : ""} to check. Tap to see.</button>` : ""}
      ${!soundOn ? `<button class="banner" id="sound2">🔔 Tap here so the phone rings for new orders</button>` : ""}
      <main class="list">${list.length ? list.map(card).join("") : `<div class="empty">${tab === "now" ? "No orders right now.<br>New ones appear here by themselves." : tab === "later" ? "No orders booked for later." : "Nothing finished yet today."}</div>`}</main>`;
    window.scrollTo(0, keepScroll);
    bind();
  }

  function whenLine(o) {
    const placed = utc(o.created_at);
    if (o.scheduled_at) {
      const s = utc(o.scheduled_at);
      const win = WINDOWS[o.scheduled_window];
      return `<span class="later">For ${win ? win + ", " : time(s) + ", "}${day(s)}</span><div class="when">Placed ${time(placed)}, ${day(placed)}</div>`;
    }
    return `<div class="when">Placed ${time(placed)} · ${ago(placed)} · as soon as possible</div>`;
  }

  function billSec(o) {
    const sub = num(o.subtotal), disc = num(o.discount_total), pack = num(o.packing_fee), gst = num(o.gst_amount);
    const fee = num(o.delivery_fee), total = num(o.total), oldFare = num(o.delivery_fee_final);
    const kitchen = sub - disc + pack;
    let pay;
    if (o.payment_method === "upi" && o.paid) pay = `<div class="paybox ok">✓ Paid ${rs(total)} by UPI</div>`;
    else if (o.payment_method === "upi") pay = `<div class="paybox wait">UPI ${rs(total)}: not confirmed yet</div>`;
    else pay = `<div class="paybox cash">Cash: collect ${rs(Math.ceil(total))}<small>${o.order_type === "pickup" ? "At the counter when they pick up." : "Tell the Porter rider to collect it, or ask the customer to pay by UPI."}</small></div>`;
    const cost = num(o.courier_cost);
    const porterBox = o.order_type === "delivery"
      ? `<div><span>Delivery money (for Porter)</span><b>${rs(fee)}</b>${cost ? `<span>Porter cost ${rs(cost)} · ${cost > fee ? rs(cost - fee) + " extra from us" : rs(fee - cost) + " left over"}</span>` : ""}</div>` : "";
    return `<div class="sec"><h3>Bill</h3><div class="bill">
        ${(o.items || []).map((i) => `<div><span>${num(i.qty)} × ${esc(i.name)}</span><span>${rs(num(i.price) * num(i.qty))}</span></div>`).join("")}
        ${disc ? `<div class="minus"><span>Discount${o.discount_code ? " (" + esc(o.discount_code) + ")" : ""}</span><span>−${rs(disc)}</span></div>` : ""}
        ${pack ? `<div><span>Packing</span><span>${rs(pack)}</span></div>` : ""}
        ${gst ? `<div><span>GST 5%</span><span>${rs(gst)}</span></div>` : ""}
        ${o.order_type === "delivery" ? `<div><span>Delivery</span><span>${fee ? rs(fee) : "—"}</span></div>` : ""}
        <div class="tot"><span>Customer pays</span><span>${rs(total)}</span></div>
        ${oldFare ? `<div><span>+ Porter fare (old order)</span><span>${rs(oldFare)}</span></div>` : ""}
      </div>
      ${pay}
      <div class="split">
        <div><span>Kitchen keeps (food + packing)</span><b>${rs(kitchen)}</b></div>
        <div><span>GST to set aside</span><b>${rs(gst)}</b></div>
        ${porterBox || `<div><span>Delivery</span><b>Pickup</b></div>`}
      </div></div>`;
  }

  // Opens the Porter / Rapido app on Android (falls back to the Play Store page).
  // Neither app accepts a pre-filled drop location from outside, so the flow is:
  // copy the location here, open the app, paste it into the Drop box.
  const appLink = (pkg) => `intent://#Intent;package=${pkg};S.browser_fallback_url=${encodeURIComponent("https://play.google.com/store/apps/details?id=" + pkg)};end`;
  const PORTER_PKG = "in.porter.customerapp", RAPIDO_PKG = "com.rapido.passenger";

  function mapsLinks(o, addr, landmark) {
    const dlat = parseFloat(o.delivery_lat), dlng = parseFloat(o.delivery_lng);
    const k = (data && data.kitchen) || {};
    const klat = parseFloat(k.lat), klng = parseFloat(k.lng);
    const nearKitchen = isFinite(klat) && isFinite(dlat) && Math.abs(klat - dlat) < 0.0012 && Math.abs(klng - dlng) < 0.0012;
    const hasPin = isFinite(dlat) && isFinite(dlng) && !nearKitchen;
    const text = (addr + (landmark ? ", " + landmark : "") + ", Chennai").trim();
    return { hasPin, drop: hasPin ? `https://www.google.com/maps/search/?api=1&query=${dlat},${dlng}` : `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(text)}` };
  }

  function porterSec(o) {
    if (o.order_type !== "delivery") return "";
    const [addr, landmark] = splitAddr(o.delivery_address);
    const k = (data && data.kitchen) || {};
    const m = mapsLinks(o, addr, landmark);
    const booked = o.sr_tracking_url || o.sr_courier;
    const flag = o.address_flagged ? `<div class="flag">⚠ ${esc(o.address_flag_reason || "Check this address.")} If it looks wrong, call the customer before booking.</div>` : "";
    const noPin = m.hasPin ? "" : `<div class="flag">⚠ The customer did not drop an exact pin. Check the landmark or call before booking.</div>`;
    const head = `<div class="sec"><h3>Deliver to</h3><div class="addr">${esc(addr)}</div>
      ${landmark ? `<div class="hint">Landmark: ${esc(landmark)}</div>` : ""}
      <a class="maplink" href="${m.drop}" target="_blank" rel="noopener">See it on the map</a>${noPin}${flag}`;
    if (booked) {
      return head + `<div class="rider" style="margin-top:10px">🛵 ${esc(o.sr_courier || "Rider booked")}${o.sr_tracking_url ? ` · <a href="${esc(o.sr_tracking_url)}" target="_blank" rel="noopener">rider link</a>` : ""}</div></div>`;
    }
    if (!["preparing", "ready"].includes(o.status)) return head + `</div>`;
    const cashNote = o.payment_method === "upi" && o.paid ? "Already paid. Rider collects nothing."
      : o.payment_method === "upi" ? `UPI not confirmed yet. Check before the rider leaves.`
      : `Rider collects ${rs(Math.ceil(num(o.total)))} cash.`;
    const d = drafts[o.id] || {};
    const dropText = addr + (landmark ? " (Landmark: " + landmark + ")" : "");
    const row = (label, value, copyText, btn) => `<div class="step-row"><div class="sr-l">${label}</div><div class="sr-v">${esc(value)}</div>
      <button class="copy" data-copy="${esc(copyText)}">${btn}</button></div>`;
    return head + `</div><div class="sec porter"><h3>Book a rider</h3>
      <div class="how"><b>How:</b> tap each green <b>Copy</b> button, open the app, and paste it in the matching box.</div>
      <div class="openapps">
        <a class="openapp" href="${appLink(PORTER_PKG)}">Open Porter</a>
        <a class="openapp" href="${appLink(RAPIDO_PKG)}">Open Rapido</a>
      </div>
      ${row("1 · Pickup (kitchen)", k.address || "34 Murrays Gate Road, Alwarpet", k.address || "", "Copy pickup")}
      ${row("2 · Drop (customer)", dropText, m.hasPin ? m.drop : dropText, m.hasPin ? "Copy map location" : "Copy drop address")}
      ${m.hasPin ? row("   or the address as text", dropText, dropText, "Copy address") : ""}
      ${row("3 · Receiver", (o.customer_name || "Customer") + " · " + prettyPhone(o.customer_phone), phone10(o.customer_phone).slice(-10), "Copy number")}
      <div class="how" style="margin-top:12px"><b>Tell the rider:</b> ${cashNote}</div>
      <div class="how">After booking, tap <b>Share</b> in the app, copy the tracking link and paste it below.</div>
      <div class="field"><label for="link-${o.id}">Rider tracking link</label>
        <input id="link-${o.id}" data-draft="link" data-id="${o.id}" inputmode="url" placeholder="https://..." value="${esc(d.link || "")}"></div>
      <div class="field"><label for="fare-${o.id}">What the rider app charged (₹)</label>
        <input id="fare-${o.id}" data-draft="fare" data-id="${o.id}" inputmode="decimal" placeholder="e.g. 62" value="${esc(d.fare || "")}">
        <div class="hint">Only for our accounts. The customer already paid ${rs(o.delivery_fee)} for delivery and is not charged again.</div></div>
      <button class="big blue" data-dispatch="${o.id}" style="margin-top:12px">I booked the rider: send link to customer</button>
      <div class="tells">The customer gets: “Your order is on its way” with the rider's live link.</div>
    </div>`;
  }

  // Steps shown as a strip so it is obvious where the order is.
  function steps(o) {
    const del = o.order_type === "delivery";
    const names = del ? ["Accepted", "Cooking", "Rider on the way", "Delivered"] : ["Accepted", "Cooking", "Ready", "Picked up"];
    const idx = { new: 0, preparing: 1, ready: del ? 1 : 2, out_for_delivery: 2, delivered: 4 }[o.status];
    if (idx === undefined) return "";
    return `<div class="steps">${names.map((n, i) => `<div class="stp ${i < idx ? "done" : i === idx ? "now" : ""}"><i>${i < idx ? "✓" : i + 1}</i><span>${n}</span></div>`).join("")}</div>`;
  }

  // Money first: the one thing that blocks Mom.
  function payNow(o) {
    if (!needsMoney(o)) return "";
    const total = rs(o.total);
    return `<div class="paynow"><div class="pn-k">💰 CHECK THE MONEY FIRST</div>
      <div class="pn-t">Did ${esc(o.customer_name || "the customer")} pay ${total}?</div>
      <div class="pn-s">Open your UPI app (GPay / PhonePe). Look for <b>${total}</b>. Tap the green button only when you can see it.</div>
      <button class="big pay" data-paid="${o.id}" data-confirm="Tap again to confirm. The customer is told you got ${total}.">Yes, I got ${total}</button>
      <div class="pn-s" style="margin-top:8px">Not there after a few minutes? <a href="tel:+${waNum(o.customer_phone)}"><b>Call ${prettyPhone(o.customer_phone)}</b></a></div></div>`;
  }

  // One plain-language "what to do now" block with the single main button.
  function nextStep(o) {
    const del = o.order_type === "delivery";
    const btn = (st, label, cls) => `<button class="big ${cls || ""}" data-do="${st}" data-id="${o.id}">${label}</button>`;
    let k, t, b = "", warn = false;
    if (o.status === "new") {
      k = "NEXT"; t = "Accept this order and start cooking"; b = btn("preparing", "Accept order") + `<div class="tells">The customer gets: “The kitchen has accepted your order.”</div>`;
    } else if (o.status === "preparing") {
      k = "NEXT"; t = del ? "Cook it and pack it. Then tap below." : "Cook it. Tap below when it is packed.";
      b = btn("ready", del ? "Food is packed and ready" : "Food is ready for pickup") + `<div class="tells">${del ? "The customer gets: “Packed and ready. We're booking your rider.”" : "The customer gets: “Your order is ready to collect.”"}</div>`;
    } else if (o.status === "ready" && !del) {
      k = "WAITING"; t = "Waiting for the customer to come and collect it."; b = btn("delivered", "Customer has collected it ✓", "blue");
    } else if (o.status === "ready" && del) {
      k = "NEXT"; t = (o.sr_tracking_url || o.sr_courier) ? "Rider is booked. Waiting for pickup." : "Book a rider. Steps are in “Book a rider” below ⬇"; 
    } else if (o.status === "out_for_delivery") {
      k = "ON THE WAY"; warn = true; t = "The rider has the food. It has NOT reached the customer yet.";
      b = `<div class="warn">Tap the button below only AFTER the customer has the food in their hand.</div>` + btn("delivered", "Customer has received the food ✓", "blue") + `<div class="tells">Tapping this tells the customer “Delivered” and asks them to rate. You cannot undo it.</div>`;
    } else return "";
    return `<div class="next ${warn ? "warnbox" : ""}"><div class="nx-k">${k}</div><div class="nx-t">${t}</div>${b}</div>`;
  }

  function actions(o) {
    const minor = [`<a href="${esc(o.track_url)}" target="_blank" rel="noopener">Customer's tracking page</a>`];
    if (o.status === "ready" && o.order_type === "delivery") minor.push(`<button data-do="delivered" data-id="${o.id}" data-confirm="Mark delivered without a rider?">Delivered without a rider</button>`);
    if (["new", "preparing"].includes(o.status)) minor.push(`<button class="danger" data-do="cancelled" data-id="${o.id}" data-confirm="Cancel order #${o.id}? The customer is told.">Cancel order</button>`);
    return `<div class="act"><div class="minor">${minor.join("")}</div></div>`;
  }

  function card(o) {
    const label = { new: "NEW", preparing: "COOKING", ready: "READY", out_for_delivery: "ON THE WAY", delivered: "DELIVERED", cancelled: "CANCELLED" }[o.status] || o.status;
    const note = (o.instructions || "").trim();
    const itemNotes = (o.items || []).filter((i) => i.note).map((i) => `${esc(i.name)}: ${esc(i.note)}`);
    return `<article class="card s-${o.status}" id="o-${o.id}">
      <div class="sec"><div class="head"><div><div class="oid">#${o.id}</div>${whenLine(o)}</div>
        <div class="pills"><span class="pill p-${o.status}">${label}</span><span class="pill p-type">${o.order_type === "pickup" ? "PICKUP" : "DELIVERY"}</span></div></div></div>
      ${OPEN.includes(o.status) ? `<div class="sec nx-wrap">${steps(o)}${payNow(o)}${nextStep(o)}</div>` : ""}
      <div class="sec cust"><div><b>${esc(o.customer_name || "Customer")}</b><div class="ph">${prettyPhone(o.customer_phone)}</div></div>
        <div class="cbtns"><a href="tel:+${waNum(o.customer_phone)}">📞 Call</a><a href="https://wa.me/${waNum(o.customer_phone)}" target="_blank" rel="noopener">WhatsApp</a></div></div>
      <div class="sec"><ul class="items">${(o.items || []).map((i) => `<li><span class="q">${num(i.qty)}×</span><span>${esc(i.name)}</span></li>`).join("")}</ul>
        ${note || itemNotes.length ? `<div class="note">📝 ${[esc(note), ...itemNotes].filter(Boolean).join("<br>")}</div>` : ""}</div>
      ${o.feedback ? `<div class="sec"><span class="pill ${o.feedback.rating === "bad" ? "p-cancelled" : o.feedback.rating === "good" ? "p-preparing" : "p-new"}">${{ good: "😋 Loved it", ok: "🙂 It was okay", bad: "😕 Not great" }[o.feedback.rating] || ""}</span>${o.feedback.comment ? `<div class="note" style="margin-top:8px">“${esc(o.feedback.comment)}”</div>` : ""}</div>` : ""}
      ${porterSec(o)}
      ${billSec(o)}
      ${OPEN.includes(o.status) ? actions(o) : `<div class="act"><div class="minor"><a href="${esc(o.track_url)}" target="_blank" rel="noopener">Customer's tracking page</a></div></div>`}
    </article>`;
  }

  // ---------- actions
  const pendingConfirm = {};
  function bind() {
    const pa = document.getElementById("payalert");
    if (pa) pa.onclick = () => { const o = groups().now.find(needsMoney); const el = o && document.getElementById("o-" + o.id); if (el) { el.scrollIntoView({ block: "start", behavior: "smooth" }); window.scrollBy(0, -150); el.classList.add("flash"); } };
    app.querySelectorAll("[data-tab]").forEach((b) => b.onclick = () => { tab = b.dataset.tab; render(); window.scrollTo(0, 0); });
    const toggle = () => { soundOn = !soundOn; try { localStorage.setItem(SOUND_KEY, soundOn ? "1" : "0"); } catch (_) {} unlockSound(); if (soundOn) ring(); render(); };
    const s1 = document.getElementById("sound"), s2 = document.getElementById("sound2");
    if (s1) s1.onclick = toggle; if (s2) s2.onclick = toggle;
    app.querySelectorAll("[data-copy]").forEach((b) => b.onclick = async () => {
      try { await navigator.clipboard.writeText(b.dataset.copy); b.textContent = "Copied ✓"; b.classList.add("done"); toast("Copied. Now open the app and paste it."); }
      catch (_) { toast("Couldn't copy. Press and hold the text instead."); }
    });
    app.querySelectorAll("[data-draft]").forEach((i) => i.oninput = () => { (drafts[i.dataset.id] = drafts[i.dataset.id] || {})[i.dataset.draft] = i.value; });
    app.querySelectorAll('[data-do="delivered"]').forEach((b) => { if (!b.dataset.confirm) b.dataset.confirm = "1"; });
    app.querySelectorAll("[data-do]").forEach((b) => b.onclick = () => {
      const id = b.dataset.id, st = b.dataset.do;
      if (b.dataset.confirm && pendingConfirm[id + st] !== true) {
        pendingConfirm[id + st] = true; b.textContent = "Tap again to confirm"; b.classList.add("sure");
        setTimeout(() => { delete pendingConfirm[id + st]; }, 5000); return;
      }
      delete pendingConfirm[id + st];
      act(b, () => api(`/api/admin/orders/${id}/status`, { method: "POST", body: JSON.stringify({ status: st }) }),
        { preparing: `Order #${id} accepted. Customer told.`, ready: `#${id} marked ready. Customer told.`, delivered: `#${id} done 🎉`, cancelled: `#${id} cancelled. Customer told.` }[st]);
    });
    app.querySelectorAll("[data-paid]").forEach((b) => b.onclick = () => {
      const id = b.dataset.paid;
      if (b.dataset.confirm && pendingConfirm[id + "paid"] !== true) {
        pendingConfirm[id + "paid"] = true; b.dataset.label = b.textContent; b.textContent = "Tap again to confirm"; b.classList.add("sure");
        setTimeout(() => { delete pendingConfirm[id + "paid"]; if (b.isConnected) { b.textContent = b.dataset.label; b.classList.remove("sure"); } }, 5000); return;
      }
      delete pendingConfirm[id + "paid"];
      act(b, () => api(`/api/admin/orders/${id}/paid`, { method: "POST" }), "Payment noted. Customer thanked.");
    });
    app.querySelectorAll("[data-dispatch]").forEach((b) => b.onclick = () => {
      const id = b.dataset.dispatch, d = drafts[id] || {};
      const link = (d.link || "").trim(), fare = parseFloat(d.fare);
      if (!link) { toast("Paste the Porter tracking link first."); document.getElementById("link-" + id)?.focus(); return; }
      if (!/^https?:\/\//.test(link)) { toast("The link should start with https://"); return; }
      act(b, () => api(`/api/admin/orders/${id}/manual-dispatch`, { method: "POST", body: JSON.stringify({ tracking_url: link, fare: fare > 0 ? fare : null }) }),
        "Rider link sent to the customer 🛵", () => { delete drafts[id]; });
    });
  }

  async function act(btn, call, okMsg, after) {
    btn.disabled = true; const old = btn.textContent; btn.textContent = "Saving…";
    try { await call(); if (after) after(); toast(okMsg || "Done"); await load(); }
    catch (e) { if (e.message !== "auth") { toast(e.message, 5000); btn.disabled = false; btn.textContent = old; } }
  }

  // ---------- polling
  async function load() {
    const fresh = await api("/api/admin/kitchen");
    const ids = new Set(fresh.orders.map((o) => o.id));
    const newOnes = seen ? fresh.orders.filter((o) => !seen.has(o.id) && o.status === "new") : [];
    const firstLoad = !seen;
    seen = ids; data = fresh;
    if (firstLoad && focusId) {
      const g = groups();
      tab = g.later.some((o) => o.id === focusId) ? "later" : g.done.some((o) => o.id === focusId) ? "done" : "now";
    }
    const typing = document.activeElement && document.activeElement.matches("input[data-draft]");
    if (!typing) render();
    if (firstLoad && focusId) {
      const el = document.getElementById("o-" + focusId);
      if (el) { el.scrollIntoView({ block: "start" }); window.scrollBy(0, -150); el.classList.add("flash"); }
      else toast(`Order #${focusId} isn't open any more.`);
      focusId = null;
    }
    if (newOnes.length) {
      ring(); tab = "now"; render();
      toast(newOnes.length === 1 ? `🔔 New order #${newOnes[0].id}` : `🔔 ${newOnes.length} new orders`, 6000);
      newOnes.forEach((o) => document.getElementById("o-" + o.id)?.classList.add("flash"));
      document.title = "🔔 New order · Kitchen"; setTimeout(() => { document.title = "Tulsi Kitchen"; }, 15000);
    }
  }
  let timer = null;
  function start() {
    app.innerHTML = `<div class="empty">Loading orders…</div>`;
    load().catch((e) => { if (e.message !== "auth") app.innerHTML = `<div class="empty">Couldn't load orders. Check the internet and pull down to retry.</div>`; });
    clearInterval(timer);
    timer = setInterval(() => { if (token) load().catch(() => {}); }, 15000);
  }
  document.addEventListener("visibilitychange", () => { if (!document.hidden && token) load().catch(() => {}); });
  document.addEventListener("click", unlockSound, { once: true });

  if (token) start(); else renderLogin();
})();
