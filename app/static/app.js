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

  const pincodeWrap = document.getElementById("pincode-wrap");
  const deliveryStatus = document.getElementById("delivery-status");
  const typeSel = document.querySelector("[name=order_type]");
  typeSel.addEventListener("change", () => {
    pincodeWrap.hidden = typeSel.value !== "delivery";
    deliveryStatus.textContent = "";
    recalc();
  });

  // Pincode-based delivery check
  const pincodeInput = document.querySelector("[name=pincode]");
  let pincodeTimer = null;
  if (pincodeInput) {
    pincodeInput.addEventListener("input", () => {
      clearTimeout(pincodeTimer);
      const pin = pincodeInput.value.trim();
      if (pin.length === 6 && /^\d{6}$/.test(pin)) {
        pincodeTimer = setTimeout(() => checkPincode(pin), 500);
      } else {
        deliveryStatus.textContent = "";
        feeRow.hidden = true;
      }
    });
  }

  async function checkPincode(pin) {
    deliveryStatus.textContent = "Checking delivery…";
    deliveryStatus.style.color = "";
    try {
      const r = await fetch(`/api/delivery/check?pincode=${pin}`);
      const d = await r.json();
      if (d.serviceable) {
        deliveryStatus.textContent = `Delivery available ${d.eta ? `(${d.eta} days)` : ""} — Fee: ${d.fee_estimate}`;
        deliveryStatus.style.color = "var(--green)";
        // Use zone-based fee estimate for now
        fee = 0;
        const sub = subtotal();
        if (sub < 700) {
          fee = 30; // Zone A estimate
          feeRow.hidden = false;
          feeVal.textContent = money(fee) + " (approx)";
          totalEl.textContent = money(sub + fee);
        } else {
          feeRow.hidden = false;
          feeVal.textContent = "Free";
          totalEl.textContent = money(sub);
        }
      } else {
        deliveryStatus.textContent = "We don't deliver to that pincode yet.";
        deliveryStatus.style.color = "#b00";
        feeRow.hidden = true;
      }
    } catch (e) {
      deliveryStatus.textContent = "";
    }
  }

  function recalc() {
    fee = 0;
    feeRow.hidden = true;
    if (typeSel.value === "delivery") {
      const pin = pincodeInput ? pincodeInput.value.trim() : "";
      if (pin.length === 6) checkPincode(pin);
      return;
    }
    totalEl.textContent = money(subtotal());
  }
  function subtotal() {
    return Object.entries(cart).reduce((a, [id, q]) => a + priceEl[id] * q, 0);
  }

  // Pre-fill saved address if phone number exists
  const phoneInput = document.querySelector("[name=phone]");
  let phoneTimer = null;
  if (phoneInput) {
    phoneInput.addEventListener("input", () => {
      clearTimeout(phoneTimer);
      const phone = phoneInput.value.trim();
      if (phone.length >= 10) {
        phoneTimer = setTimeout(() => prefilled = loadSavedAddress(phone), 500);
      }
    });
  }

  async function loadSavedAddress(phone) {
    try {
      const r = await fetch(`/api/customer/${phone}`);
      const d = await r.json();
      if (d.exists) {
        if (d.address) {
          const addrInput = document.querySelector("[name=address]");
          if (addrInput && !addrInput.value) addrInput.value = d.address;
        }
        if (d.pincode) {
          const pinInput = document.querySelector("[name=pincode]");
          if (pinInput && !pinInput.value) {
            pinInput.value = d.pincode;
            if (d.pincode.length === 6) checkPincode(d.pincode);
          }
        }
        if (d.name) {
          const nameInput = document.querySelector("[name=name]");
          if (nameInput && !nameInput.value) nameInput.value = d.name;
        }
      }
    } catch (e) {}
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
      pincode: fd.get("order_type") === "delivery" ? fd.get("pincode") : null,
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
      msg.textContent = `Order #${data.order_id} placed. Total ${money(data.total)}. We'll WhatsApp you when it's dispatched!`;
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
