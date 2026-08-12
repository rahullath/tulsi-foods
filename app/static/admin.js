(() => {
  const TOKEN_KEY = "tulsi_admin_token";
  const saveState = document.getElementById("save-state");
  let token = localStorage.getItem(TOKEN_KEY);

  if (!token) {
    token = prompt("Admin token:");
    if (!token) { saveState.textContent = "No token — refresh to retry"; return; }
    localStorage.setItem(TOKEN_KEY, token);
  }

  const headers = { "X-Admin-Token": token };

  async function api(url, opts = {}) {
    const res = await fetch(url, { ...opts, headers: { ...headers, ...(opts.headers || {}) } });
    if (res.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      location.reload();
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Request failed");
    return data;
  }

  const checkboxes = Array.from(document.querySelectorAll(".avail-check"));

  async function load() {
    const d = await api("/api/admin/availability");
    const on = new Set(d.available_ids);
    checkboxes.forEach((c) => { c.checked = on.has(c.dataset.id); });
    if (d.last_day) saveState.textContent = `copied so far from ${d.last_day}`;
  }

  let saveTimer = null;
  checkboxes.forEach((c) => c.addEventListener("change", () => {
    saveState.textContent = "Saving…";
    clearTimeout(saveTimer);
    saveTimer = setTimeout(save, 400);
  }));

  async function save() {
    try {
      await api("/api/admin/availability", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          available_ids: checkboxes.filter((c) => c.checked).map((c) => c.dataset.id),
          unavailable_ids: checkboxes.filter((c) => !c.checked).map((c) => c.dataset.id),
        }),
      });
      saveState.textContent = "Saved ✓";
    } catch (err) {
      saveState.textContent = "Save failed: " + err.message;
    }
  }

  document.getElementById("repeat-yesterday").addEventListener("click", async () => {
    saveState.textContent = "Copying yesterday…";
    try {
      const d = await api("/api/admin/availability/repeat-yesterday", { method: "POST" });
      const on = new Set((await api("/api/admin/availability")).available_ids);
      checkboxes.forEach((c) => { c.checked = on.has(c.dataset.id); });
      saveState.textContent = `Copied ${d.copied_items} items from ${d.copied_from} ✓`;
    } catch (err) {
      saveState.textContent = "Copy failed: " + err.message;
    }
  });

  load().catch((err) => { saveState.textContent = "Load failed: " + err.message; });
})();
