"""Structured snapshot extraction.

Beyond the static copy, the crawler collects a machine-readable view of each
page from inside the browser:

- embedded app states (__NEXT_DATA__, __remixContext, __NUXT__, Apollo/Redux
  stores, ld+json) — SSR sites often embed their full data there
- every image with its BEST available variant (largest srcset candidate)
- computed design tokens (fonts, colors, theme-color)
- heuristic product cards (name/price/description/image containers)

Everything is written to <output>/snapshot.json so downstream tooling can
consume the site's data without re-parsing HTML.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUTO_SCROLL_JS = """
async () => {
  await new Promise((done) => {
    let total = 0;
    const step = () => {
      window.scrollBy(0, 900);
      total += 900;
      if (total >= document.body.scrollHeight + 1800) { window.scrollTo(0, 0); done(); }
      else setTimeout(step, 120);
    };
    step();
  });
}
"""

EXTRACT_JS = r"""
() => {
  const abs = (u) => { try { return new URL(u, location.href).href } catch (e) { return u } };

  // Images: the largest srcset candidate wins over the rendered src.
  const images = [];
  document.querySelectorAll('img').forEach((img) => {
    const src = img.currentSrc || img.src;
    if (!src || src.startsWith('data:')) return;
    let bestUrl = abs(src);
    let bestWidth = img.naturalWidth || 0;
    const srcset = img.getAttribute('srcset') || '';
    for (const cand of srcset.split(',')) {
      const parts = cand.trim().split(/\s+/);
      const w = parts[1] && parts[1].endsWith('w') ? parseInt(parts[1]) : 0;
      if (parts[0] && w > bestWidth) { bestWidth = w; bestUrl = abs(parts[0]); }
    }
    images.push({
      url: abs(src), best_url: bestUrl,
      width: img.naturalWidth || 0, height: img.naturalHeight || 0,
      alt: img.alt || '',
    });
  });

  // Embedded app states: SSR frameworks ship their loader data here.
  const states = {};
  for (const key of ['__remixContext', '__NEXT_DATA__', '__NUXT__', '__APOLLO_STATE__', '__INITIAL_STATE__', '__PRELOADED_STATE__']) {
    try {
      const val = key === '__NEXT_DATA__'
        ? JSON.parse((document.getElementById('__NEXT_DATA__') || {}).textContent || 'null')
        : window[key];
      if (val) states[key] = JSON.parse(JSON.stringify(val));
    } catch (e) { /* state not serializable */ }
  }
  const ldjson = [];
  document.querySelectorAll('script[type="application/ld+json"]').forEach((s) => {
    try { ldjson.push(JSON.parse(s.textContent || '')) } catch (e) { /* invalid */ }
  });
  if (ldjson.length) states['ld+json'] = ldjson;

  // Design tokens: what the browser actually computed.
  const style = (el, props) => {
    if (!el) return null;
    const c = getComputedStyle(el);
    const out = {};
    for (const p of props) out[p] = c.getPropertyValue(p);
    return out;
  };
  const design = {
    body: style(document.body, ['font-family', 'color', 'background-color']),
    heading: style(document.querySelector('h1, h2, h3'), ['font-family', 'font-weight', 'color']),
    button: style(document.querySelector('button, [class*="btn"], a[class*="button"]'), ['background-color', 'color', 'border-radius', 'font-family']),
    theme_color: (document.querySelector('meta[name="theme-color"]') || {}).content || null,
  };

  // Heuristic product cards: smallest container with one image + a price.
  const products = [];
  const seen = new Set();
  const PRICE_RE = /[$€£]\s?(\d{1,5}(?:[.,]\d{2})?)/;
  document.querySelectorAll('div, li, article, a').forEach((el) => {
    const text = (el.textContent || '').trim();
    if (text.length > 400 || !PRICE_RE.test(text)) return;
    const img = el.querySelector('img');
    if (!img || el.querySelectorAll('img').length > 1) return;
    const nameEl = el.querySelector('h1,h2,h3,h4,strong,[class*="name" i],[class*="title" i]');
    const name = ((nameEl && nameEl.textContent) || img.alt || '').trim();
    if (!name || name.length > 90 || seen.has(name)) return;
    seen.add(name);
    const price = parseFloat(PRICE_RE.exec(text)[1].replace(',', ''));
    const descEl = el.querySelector('p');
    products.push({
      name: name,
      price: isFinite(price) ? price : null,
      description: ((descEl && descEl.textContent) || '').trim().slice(0, 300),
      image: abs(img.currentSrc || img.src),
    });
  });

  return { title: document.title, images: images, states: states, design: design, products: products };
}
"""


def best_images(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate images across pages, keeping the widest variant per alt/url."""

    best: dict[str, dict[str, Any]] = {}
    for page in pages:
        for img in page.get("images", []):
            key = img.get("alt") or img.get("url")
            prev = best.get(key)
            if not prev or (img.get("width") or 0) > (prev.get("width") or 0):
                best[key] = img
    return list(best.values())


def write_snapshot(output_dir: Path, start_url: str, pages: list[dict[str, Any]], assets_saved: int) -> Path:
    snapshot = {
        "origin": start_url,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pages_visited": len(pages),
        "assets_saved": assets_saved,
        "pages": pages,
        "images": best_images(pages),
    }
    path = output_dir / "snapshot.json"
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
