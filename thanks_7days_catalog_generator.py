#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import html
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin

import requests

COLLECTION_JSON = "https://www.isseymiyake.com/collections/thanks-7days/products.json?limit=250&page={page}"
PRODUCT_BASE = "https://www.isseymiyake.com/products/"
OUTPUT = Path("index.html")

JST = timezone(timedelta(hours=9))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en;q=0.9,ko;q=0.8",
}


def yen(v):
    try:
        n = int(v)
        return f"¥{n:,}"
    except Exception:
        return "-"


def fetch_products(max_pages=20):
    session = requests.Session()
    products = []
    for page in range(1, max_pages + 1):
        url = COLLECTION_JSON.format(page=page)
        r = session.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        data = r.json()
        batch = data.get("products", [])
        if not batch:
            break
        products.extend(batch)
        if len(batch) < 250:
            break
        time.sleep(0.5)
    return products


def first_image(product):
    images = product.get("images") or []
    if images:
        return images[0].get("src") or ""
    return ""


def available_info(product):
    variants = product.get("variants") or []
    available_variants = [v for v in variants if v.get("available") is True]
    return len(available_variants), len(variants)


def best_price(product):
    variants = product.get("variants") or []
    prices = []
    compares = []
    for v in variants:
        if v.get("price"):
            prices.append(v.get("price"))
        if v.get("compare_at_price"):
            compares.append(v.get("compare_at_price"))
    price = min(prices, key=lambda x: int(x)) if prices else None
    compare = max(compares, key=lambda x: int(x)) if compares else None
    return price, compare


def product_card(product):
    title = html.escape(product.get("title") or "No title")
    handle = product.get("handle") or ""
    link = PRODUCT_BASE + handle if handle else "#"
    img = first_image(product)
    price, compare = best_price(product)
    avail, total_variants = available_info(product)
    updated = product.get("updated_at") or ""
    tags = product.get("tags") or []
    tag_text = ", ".join([t for t in tags if "THANKS" in t or "優待" in t or "再入荷" in t or "公開" in t][:6])

    stock_class = "in" if avail > 0 else "out"
    stock_text = f"재고 있음 {avail}/{total_variants}" if avail > 0 else "품절"

    img_html = f'<img src="{html.escape(img)}" alt="{title}" loading="lazy">' if img else '<div class="noimg">No Image</div>'
    compare_html = f'<span class="compare">{yen(compare)}</span>' if compare else ''

    return f"""
    <article class="card" data-title="{title.lower()}" data-stock="{stock_class}">
      <a class="image" href="{html.escape(link)}" target="_blank" rel="noopener">{img_html}</a>
      <div class="body">
        <div class="stock {stock_class}">{stock_text}</div>
        <h2>{title}</h2>
        <div class="price"><strong>{yen(price)}</strong> {compare_html}</div>
        <div class="meta">updated: {html.escape(updated)}</div>
        <div class="tags">{html.escape(tag_text)}</div>
        <a class="btn" href="{html.escape(link)}" target="_blank" rel="noopener">상품 페이지 열기</a>
      </div>
    </article>
    """


def build_html(products):
    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")
    total = len(products)
    available_products = sum(1 for p in products if available_info(p)[0] > 0)
    cards = "\n".join(product_card(p) for p in products)

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>THANKS 7DAYS Catalog</title>
<style>
  :root {{ --bg:#f6f3ee; --card:#fff; --text:#1d1b18; --muted:#777; --line:#e8e0d5; --accent:#111; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:Arial, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; background:var(--bg); color:var(--text); }}
  header {{ position:sticky; top:0; z-index:10; background:rgba(246,243,238,.94); backdrop-filter:blur(8px); border-bottom:1px solid var(--line); padding:18px 20px; }}
  .head {{ max-width:1200px; margin:0 auto; display:flex; gap:14px; align-items:flex-end; justify-content:space-between; flex-wrap:wrap; }}
  h1 {{ margin:0; font-size:24px; letter-spacing:.02em; }}
  .summary {{ color:var(--muted); font-size:13px; line-height:1.6; }}
  .tools {{ max-width:1200px; margin:14px auto 0; display:flex; gap:8px; flex-wrap:wrap; }}
  input, select {{ border:1px solid var(--line); background:#fff; padding:10px 12px; border-radius:10px; font-size:14px; }}
  input {{ flex:1; min-width:220px; }}
  main {{ max-width:1200px; margin:24px auto; padding:0 20px 40px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:18px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:18px; overflow:hidden; box-shadow:0 8px 22px rgba(0,0,0,.04); }}
  .image {{ display:block; aspect-ratio:5/7; background:#eee; overflow:hidden; }}
  .image img {{ width:100%; height:100%; object-fit:cover; display:block; transition:transform .25s ease; }}
  .image:hover img {{ transform:scale(1.03); }}
  .noimg {{ height:100%; display:flex; align-items:center; justify-content:center; color:var(--muted); }}
  .body {{ padding:14px; }}
  .stock {{ display:inline-block; font-size:12px; padding:5px 8px; border-radius:999px; margin-bottom:9px; }}
  .stock.in {{ background:#e6f7e9; color:#17722c; }}
  .stock.out {{ background:#f3e3e3; color:#9b2222; }}
  h2 {{ font-size:15px; line-height:1.35; margin:0 0 10px; min-height:40px; }}
  .price {{ font-size:14px; margin-bottom:8px; }}
  .price strong {{ font-size:16px; }}
  .compare {{ color:var(--muted); text-decoration:line-through; margin-left:6px; }}
  .meta, .tags {{ font-size:11px; color:var(--muted); line-height:1.45; min-height:16px; }}
  .btn {{ display:block; text-align:center; margin-top:12px; padding:10px 12px; border-radius:12px; background:var(--accent); color:#fff; text-decoration:none; font-size:13px; }}
  .hidden {{ display:none !important; }}
  footer {{ max-width:1200px; margin:0 auto 30px; padding:0 20px; color:var(--muted); font-size:12px; }}
</style>
</head>
<body>
<header>
  <div class="head">
    <div>
      <h1>THANKS 7DAYS Catalog</h1>
      <div class="summary">총 {total}개 상품 · 재고 있음 {available_products}개 · 마지막 갱신 {now}</div>
    </div>
  </div>
  <div class="tools">
    <input id="q" type="search" placeholder="상품명 검색">
    <select id="stock">
      <option value="all">전체</option>
      <option value="in">재고 있음</option>
      <option value="out">품절</option>
    </select>
  </div>
</header>
<main>
  <div class="grid" id="grid">
    {cards}
  </div>
</main>
<footer>
  로그인 없이 공개되는 products.json 데이터를 바탕으로 생성된 카탈로그입니다. 실제 회원 할인가는 로그인 후 상품 페이지에서 확인하세요.
</footer>
<script>
const q = document.getElementById('q');
const stock = document.getElementById('stock');
const cards = [...document.querySelectorAll('.card')];
function applyFilter() {{
  const term = q.value.trim().toLowerCase();
  const s = stock.value;
  cards.forEach(card => {{
    const okTerm = !term || card.dataset.title.includes(term);
    const okStock = s === 'all' || card.dataset.stock === s;
    card.classList.toggle('hidden', !(okTerm && okStock));
  }});
}}
q.addEventListener('input', applyFilter);
stock.addEventListener('change', applyFilter);
</script>
</body>
</html>"""


def main():
    products = fetch_products()
    html_text = build_html(products)
    OUTPUT.write_text(html_text, encoding="utf-8")
    print(f"created {OUTPUT} with {len(products)} products")


if __name__ == "__main__":
    main()
