# Tulsi Foods — SEO Playbook (standing practice)

Why this exists: SEO used to be rediscovered every round. It isn't anymore.
**Every new page or feature must pass the checklist below before it ships.**
The audit script at the bottom re-verifies the whole site in seconds — run it
after any template/route change.

Status legend: `[ ]` todo · `[x]` done

## 1. The checklist (all public pages)

- `[x]` **One `<title>`, unique per page**, `Primary keyword | Tulsi Foods, Mylapore`-shaped.
- `[x]` **One meta description, unique per page**, 120–160 chars, mentions
  Mylapore/Chennai + what the page does.
- `[x]` **Canonical URL** (`<link rel="canonical">`) — absolute `https://tulsifoods.app/...`.
- `[x]` **Exactly one `<h1>`, unique text per page**, describing the page
  (fixed Sep 2026: `/menu` had none → "Today's menu"; `/bio` used a div → h1).
- `[x]` **JSON-LD parses as JSON on every page.** HARD RULE (see §3): every
  value interpolated into JSON-LD uses Jinja's `| tojson` filter — no bare
  `{{ x }}`, no Python ternaries in markup (broke all 10 category pages' ItemList, Sep 2026).
- `[x]` **Right JSON-LD type per page** (see §4 table).
- `[x]` **In the sitemap.** Automatic for any `@app.get(..., response_class=HTMLResponse)`
  route (auto-discovery in `sitemap_xml()`); add data-file freshness via
  `SITEMAP_DATA_FILES` for data-backed pages (`/updates` pattern).
- `[x]` **No orphans:** the shared nav + shared footer link every public page,
  so any new page is linked site-wide the moment it uses `base.html`.
  Verify: every public page's HTML contains the core links + its own URL is in the sitemap.
- `[x]` **Every `<img>` has `alt`** (dish photos: `"<Dish>, pure vegetarian, Tulsi Foods Mylapore"`-shaped).
- `[x]` **Breadcrumbs** on deep pages (item + category), with `BreadcrumbList` JSON-LD.
- `[x]` **robots.txt** allows the page (only `/admin`, `/kitchen`, `/api/`, `/order-actions` are blocked) and names the sitemap.
- `[x]` **llms.txt** lists the page (it feeds AI recommenders — same audience as Google).
- `[x]` **Mobile:** inherits viewport + burger nav + footer from `base.html`; no `display:none` without a replacement.

## 2. Hard rules learned the painful way

1. **JSON-LD values always go through `| tojson`.** Jinja `{{ }}` does HTML-escaping,
   not JSON-escaping — a dish name with a quote breaks the block and Google drops
   ALL structured data on the page. Concat inside the filter: `{{ (a ~ b) | tojson }}`.
2. **Most templates skip `style.css`** (`{% block styles %}{% endblock %}`), so shared
   components (`_nav.html`, `_footer.html`) carry their own `<style>`. Never assume
   a global stylesheet rule reaches a page.
3. **New route ⇒ check three places:** template context has `categories` (nav dropdown),
   `SITEMAP_TEMPLATES`/`SITEMAP_DATA_FILES` for lastmod, llms.txt `## Pages` list.

## 3. Keyword intents → pages

| Intent | Primary page | Support |
|---|---|---|
| Tulsi Foods menu / menu price | `/menu` | category pages, item pages, llms.txt prices |
| Pure veg restaurant Mylapore | `/` | `/about`, `/bio` |
| North Indian food Alwarpet / Teynampet | `/` | `/delivery` (area list) |
| Best thali Mylapore | `/category/thalis-combos` | `/menu/north-indian-thali`, `/menu/mini-thali` |
| Pav bhaji / chole bhature near Mylapore | item pages | `/category/chaats-snacks` |
| Jain food Mylapore / no onion garlic | `/` (facts), `/about` (FAQ) | item pages (customize notes) |
| Order food online Mylapore | `/menu` | `/delivery` (how it works), `/track` |
| Tulsi Foods delivery / tracking | `/track`, `/delivery` | `/updates` (tracking launch post) |
| Tulsi Foods reviews / timings | `/about` (stats + hours) | `/bio`, footer aka-line |
| Tulsi Foods offers | `/updates` (offer-kind entries) | landing teaser |

Entity anchors repeated verbatim everywhere (footer aka-line + llms.txt):
"Tulasi Foods, Thulasi Restaurant · 34 Murrays Gate Road, Alwarpet, Chennai 600018".

## 4. Per-page status (audited Sep 2026 — all passing)

| Page | Title/D/Canon | h1 | JSON-LD | Sitemap |
|---|---|---|---|---|
| `/` | ✓ | "North Indian food, cooked the way it is at home." | Restaurant, FAQPage | ✓ |
| `/menu` | ✓ | "Today's menu" | Menu | ✓ |
| `/menu/{id}` (×150) | ✓ unique | dish name | Product, BreadcrumbList | ✓ |
| `/category` | ✓ | "Browse the menu by category" (+10 h2s) | ItemList, BreadcrumbList | ✓ |
| `/category/{slug}` (×10) | ✓ unique | group name | ItemList, BreadcrumbList | ✓ |
| `/track`, `/track/{ref}` | ✓ | "Where's my order?" / status-driven | — (app surface) | ✓ (`/track`) |
| `/delivery` | ✓ | "Where we deliver, and what it costs" | FAQPage | ✓ |
| `/about` | ✓ | "Kavita Lath, cooking in Mylapore since 2015" | FAQPage | ✓ |
| `/bio` | ✓ | "Tulsi Foods" | — (link hub) | ✓ |
| `/updates` + `/updates.xml` | ✓ | "Fresh from the Kitchen" | Blog, BlogPosting | ✓ (+RSS) |
| `/404` | ✓ | "Looks like this dish fell off the menu." | — | ✓ |
| `/privacy-policy`, `/refund-cancellation-policy` | ✓ | policy names | — | ✓ |

## 5. Re-audit (run after any template/route change)

```python
import re, json
from collections import Counter
from app.main import app, all_categories
from fastapi.testclient import TestClient
c = TestClient(app)
with c:  # context manager triggers db.init_db() startup
    cats = [x["slug"] for x in all_categories()]
    pages = ["/", "/menu", "/track", "/delivery", "/about", "/bio",
             "/404", "/updates", "/category", "/privacy-policy", "/refund-cancellation-policy"] \
        + [f"/category/{s}" for s in cats] + ["/menu/north-indian-thali"]
    sm = c.get("/sitemap.xml").text
    titles, h1s, bad_ld = [], [], []
    for p in pages:
        html = c.get(p).text
        assert c.get(p).status_code == 200, p
        assert f"<loc>https://tulsifoods.app{p}</loc>" in sm, f"{p} missing from sitemap"
        titles.append(re.search(r"<title>(.*?)</title>", html, re.S).group(1))
        assert re.search(r'<meta name="description" content="(.+?)"', html, re.S), f"{p} no meta desc"
        assert '<link rel="canonical"' in html, f"{p} no canonical"
        h1s += re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.S)
        for ld in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
            try: json.loads(ld)
            except Exception as e: bad_ld.append((p, str(e)[:60]))
        for img in re.findall(r"<img\b[^>]*>", html):
            assert "alt=" in img, f"{p} img without alt: {img[:60]}"
    assert len(h1s) == len(pages), f"h1 count {len(h1s)} != pages {len(pages)}"
    assert not [t for t, n in Counter(titles).items() if n > 1], "dup titles"
    assert not bad_ld, bad_ld
    print("SEO AUDIT GREEN:", len(pages), "pages")
```
