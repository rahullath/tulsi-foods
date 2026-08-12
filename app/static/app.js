(() => {
  const cart = JSON.parse(localStorage.getItem("tulsi_cart") || "{}");
  const cartEl = document.getElementById("cart");
  const fab = document.getElementById("cart-fab");
  const qtyEls = document.querySelectorAll("[data-role=qty]");
  const priceEl = {};

  document.querySelectorAll(".item").forEach((li) => {
    const id = li.dataset.id;
    const price = parseInt(li.querySelector(".price").textContent.replace(/\D/g, ""), 10);
    priceEl[id] = price;
  });

  const money = (n) => "₹" + (Math.round(n * 100) / 100).toLocaleString("en-IN");

  function render() {
    document.querySelectorAll("[data-role=qty]").forEach((el) => {
      const id = el.closest(".item").dataset.id;
      el.textContent = cart[id] || 0;
    });
    const list = document.getElementById("cart-items");
    list.innerHTML = "";
    let sub = 0;
    for (const [id, qty] of Object.entries(cart)) {
      if (!qty) continue;
      const name = document.querySelector(`.item[data-id="${id}"] .name`).textContent.trim();
      sub += priceEl[id] * qty;
      const li = document.createElement("li");
      li.innerHTML = `<span>${name} × ${qty}</span><span>${money(priceEl[id] * qty)}</span>`;
      list.appendChild(li);
    }
    document.getElementById("subtotal").textContent = money(sub);
    const count = Object.values(cart).reduce((a, b) => a + b, 0);
    document.getElementById("fab-count").textContent = count;
    fab.classList.toggle("hidden", count === 0);
    const feeEl = document.getElementById("fee-row");
    if (feeEl.hidden) {
      document.getElementById("total").textContent = money(sub);
    }
    localStorage.setItem("tulsi_cart", JSON.stringify(cart));
  }

  document.querySelectorAll(".stepper").forEach((s) => {
    s.addEventListener("click", (e) => {
      const btn = e.target.closest("button");
      if (!btn) return;
      const id = s.dataset.id;
      cart[id] = Math.max(0, (cart[id] || 0) + (btn.dataset.act === "inc" ? 1 : -1));
      render();
      if (btn.dataset.act === "inc") openCart();
    });
  });

  function openCart() {
    cartEl.classList.remove("hidden");
    document.getElementById("cart-toggle").textContent = "▾";
    if (document.getElementById("cart-body").hidden) {
      document.getElementById("cart-body").hidden = false;
    }
  }
  fab.addEventListener("click", openCart);
  document.getElementById("cart-toggle").addEventListener("click", () => {
    const body = document.getElementById("cart-body");
    body.hidden = !body.hidden;
    document.getElementById("cart-toggle").textContent = body.hidden ? "▴" : "▾";
  });

  const feeRow = document.getElementById("fee-row");
  const feeVal = document.getElementById("delivery-fee");
  const totalEl = document.getElementById("total");
  let fee = 0;

  const kmWrap = document.getElementById("km-wrap");
  const typeSel = document.querySelector("[name=order_type]");
  typeSel.addEventListener("change", () => { kmWrap.hidden = typeSel.value !== "delivery"; recalc(); });
  document.querySelector("[name=km]").addEventListener("change", recalc);

  function recalc() {
    fee = 0;
    feeRow.hidden = true;
    if (typeSel.value === "delivery") {
      const km = parseFloat(document.querySelector("[name=km]").value);
      const sub = subtotal();
      fetch(`/api/delivery?km=${km}&subtotal=${sub}`).then((r) => r.json()).then((z) => {
        if (z.fee === null) { fee = null; feeRow.hidden = false; feeVal.textContent = "outside area"; }
        else {
          fee = z.fee;
          feeRow.hidden = false;
          feeVal.textContent = money(fee);
          totalEl.textContent = money(sub + fee);
        }
      });
      return;
    }
    totalEl.textContent = money(subtotal());
  }
  function subtotal() {
    return Object.entries(cart).reduce((a, [id, q]) => a + priceEl[id] * q, 0);
  }

  const form = document.getElementById("checkout");
  const msg = document.getElementById("order-msg");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const items = Object.entries(cart).filter(([, q]) => q > 0).map(([id, qty]) => ({ item_id: id, qty }));
    if (!items.length) { msg.textContent = "Cart is empty"; msg.className = "err"; return; }
    const fd = new FormData(form);
    const payload = {
      name: fd.get("name"), phone: fd.get("phone"), order_type: fd.get("order_type"),
      payment_method: fd.get("payment_method"), instructions: fd.get("instructions"),
      address: fd.get("address") || null,
      km: fd.get("order_type") === "delivery" ? parseFloat(fd.get("km")) : null,
      items,
    };
    msg.textContent = "Placing order…";
    msg.className = "";
    try {
      const res = await fetch("/api/orders", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) { msg.textContent = data.detail || "Could not place order"; msg.className = "err"; return; }
      msg.textContent = `Order #${data.order_id} placed. Total ${money(data.total)}. We'll call/WhatsApp you on confirmation.`;
      msg.className = "ok";
      localStorage.removeItem("tulsi_cart");
      Object.keys(cart).forEach((k) => delete cart[k]);
      render();
    } catch (err) {
      msg.textContent = "Network error, please try again"; msg.className = "err";
    }
  });

  render();
})();
