import html
import json
import time
from collections import Counter
from datetime import datetime, timezone, timedelta

import requests

COLLECTION_PAGE_URL = "https://www.isseymiyake.com/collections/thanks-7days?filter.p.vendor=&sort_by=manual&filter.v.availability=1"
COLLECTION_JSON_BASE = "https://www.isseymiyake.com/collections/thanks-7days/products.json"
PRODUCT_BASE_URL = "https://www.isseymiyake.com/products/"
OUTPUT_FILE = "index.html"

LIMIT = 250
MAX_PAGES = 20
REQUEST_SLEEP_SEC = 0.8


def yen(value):
    try:
        return f"{int(value):,}円"
    except Exception:
        return "-"


def fetch_json_page(session, page):
    params = {
        "limit": LIMIT,
        "page": page,
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json,text/plain,*/*",
        "Referer": COLLECTION_PAGE_URL,
    }
    response = session.get(COLLECTION_JSON_BASE, params=params, headers=headers, timeout=25)
    response.raise_for_status()
    data = response.json()
    return data.get("products", [])


def fetch_all_products():
    session = requests.Session()
    products = []
    seen_ids = set()

    for page in range(1, MAX_PAGES + 1):
        page_products = fetch_json_page(session, page)
        print(f"page={page}, products={len(page_products)}")

        if not page_products:
            break

        new_count = 0
        for product in page_products:
            pid = product.get("id")
            if pid in seen_ids:
                continue
            seen_ids.add(pid)
            products.append(product)
            new_count += 1

        if len(page_products) < LIMIT:
            break

        if new_count == 0:
            break

        time.sleep(REQUEST_SLEEP_SEC)

    return products


def product_available(product):
    return any(v.get("available") is True for v in product.get("variants", []))


def stock_counts(product):
    variants = product.get("variants") or []
    total = len(variants)
    available = sum(1 for v in variants if v.get("available") is True)
    soldout = total - available
    return available, soldout, total


def first_image(product):
    images = product.get("images") or []
    if images:
        return images[0].get("src", "")
    return ""


def first_variant(product):
    variants = product.get("variants") or []
    if variants:
        return variants[0]
    return {}


def build_variant_stock_html(product):
    variants = product.get("variants") or []
    if not variants:
        return '<div class="variant empty">옵션 정보 없음</div>'

    rows = []
    for variant in variants:
        title = html.escape(variant.get("title") or "옵션")
        sku = html.escape(variant.get("sku") or "")
        available = variant.get("available") is True
        cls = "variant available-variant" if available else "variant soldout-variant"
        text = "재고 있음" if available else "품절"
        sku_part = f'<span class="sku">{sku}</span>' if sku else ""

        row = f"""
            <div class="{cls}">
                <span class="variant-name">{title}</span>
                {sku_part}
                <span class="variant-status">{text}</span>
            </div>
        """
        rows.append(row)

    return "\n".join(rows)


def sort_products(products):
    return sorted(
        products,
        key=lambda p: (
            not product_available(p),
            str(p.get("vendor", "")),
            str(p.get("title", "")),
            str(p.get("updated_at", "")),
        ),
    )


def build_brand_buttons(products):
    counter = Counter((p.get("vendor") or "UNKNOWN") for p in products)
    brands = sorted(counter.keys())

    buttons = [
        f'<button class="brand-button active" data-brand="ALL">전체 브랜드 <span>{len(products)}</span></button>'
    ]

    for brand in brands:
        safe_brand = html.escape(brand)
        count = counter[brand]
        buttons.append(
            f'<button class="brand-button" data-brand="{safe_brand}">{safe_brand} <span>{count}</span></button>'
        )

    return "\n".join(buttons)


def build_html(products):
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S JST")

    products = sort_products(products)
    cards = []

    for product in products:
        title = html.escape(product.get("title", "No title"))
        vendor = html.escape(product.get("vendor") or "UNKNOWN")
        handle = product.get("handle", "")
        url = PRODUCT_BASE_URL + handle if handle else "#"
        image = first_image(product)
        available = product_available(product)
        available_count, soldout_count, variant_total = stock_counts(product)

        variant = first_variant(product)
        price = yen(variant.get("price"))
        compare_price = yen(variant.get("compare_at_price"))

        tags = product.get("tags") or []
        tag_text = ", ".join(tags[:8])
        tag_text = html.escape(tag_text)

        updated_at = html.escape(str(product.get("updated_at", "")))
        published_at = html.escape(str(product.get("published_at", "")))

        status_class = "available" if available else "soldout"
        status_text = "재고 있음" if available else "전체 품절"
        variant_stock_html = build_variant_stock_html(product)

        card = f"""
        <article class="card" data-brand="{vendor}" data-available="{'1' if available else '0'}">
            <a href="{html.escape(url)}" target="_blank" rel="noopener">
                <div class="image-wrap">
                    <img src="{html.escape(image)}" alt="{title}" loading="lazy">
                </div>
            </a>
            <div class="content">
                <div class="top-line">
                    <div class="status {status_class}">{status_text}</div>
                    <div class="stock-count">옵션 {available_count}/{variant_total}</div>
                </div>
                <div class="vendor">{vendor}</div>
                <h2>{title}</h2>
                <p class="price">가격: {price}</p>
                <p class="compare">정상가: {compare_price}</p>

                <div class="stock-box">
                    <div class="stock-title">옵션별 재고</div>
                    {variant_stock_html}
                </div>

                <p class="date">updated: {updated_at}</p>
                <p class="date">published: {published_at}</p>
                <p class="tags">{tag_text}</p>
                <a class="button" href="{html.escape(url)}" target="_blank" rel="noopener">상품 보기</a>
            </div>
        </article>
        """
        cards.append(card)

    total = len(products)
    available_products = sum(1 for p in products if product_available(p))
    total_variants = sum(len(p.get("variants") or []) for p in products)
    available_variants = sum(stock_counts(p)[0] for p in products)
    soldout_variants = total_variants - available_variants
    brand_buttons = build_brand_buttons(products)

    brand_counts = Counter((p.get("vendor") or "UNKNOWN") for p in products)
    brand_counts_json = html.escape(json.dumps(brand_counts, ensure_ascii=False))

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="300">
<title>THANKS 7DAYS Catalog</title>
<style>
    body {{
        margin: 0;
        font-family: Arial, sans-serif;
        background: #f5f5f3;
        color: #222;
    }}
    header {{
        position: sticky;
        top: 0;
        z-index: 20;
        background: rgba(255,255,255,0.96);
        border-bottom: 1px solid #ddd;
        padding: 18px 24px;
        backdrop-filter: blur(8px);
    }}
    h1 {{
        margin: 0 0 8px;
        font-size: 24px;
        text-align: center;
        letter-spacing: 0.02em;
    }}
    .summary {{
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        font-size: 13px;
        color: #444;
        justify-content: center;
    }}
    .summary span {{
        background: #fff;
        border: 1px solid #ddd;
        border-radius: 999px;
        padding: 5px 10px;
    }}
    .source {{
        margin-top: 8px;
        font-size: 12px;
        color: #777;
        text-align: center;
    }}
    .source a {{
        color: #555;
    }}
    .toolbar {{
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        align-items: center;
        justify-content: center;
        margin-top: 14px;
    }}
    .brand-toggle {{
        border: 1px solid #ccc;
        background: #fff;
        border-radius: 999px;
        padding: 9px 14px;
        font-weight: bold;
        cursor: pointer;
    }}
    .brand-panel {{
        display: none;
        max-width: 760px;
        margin: 12px auto 0;
        background: #fff;
        border: 1px solid #ddd;
        border-radius: 14px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        padding: 12px;
    }}
    .brand-panel.open {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
        gap: 8px;
    }}
    .brand-button {{
        border: 1px solid #ddd;
        background: #fafafa;
        border-radius: 10px;
        padding: 10px;
        text-align: left;
        cursor: pointer;
        font-weight: bold;
        color: #222;
    }}
    .brand-button span {{
        float: right;
        color: #777;
        font-weight: normal;
    }}
    .brand-button.active {{
        background: #222;
        color: #fff;
        border-color: #222;
    }}
    .brand-button.active span {{
        color: #ddd;
    }}
    .current-filter {{
        text-align: center;
        margin-top: 8px;
        font-size: 13px;
        color: #333;
        font-weight: bold;
    }}
    .grid {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        gap: 18px;
        padding: 22px;
    }}
    .card {{
        background: #fff;
        border: 1px solid #ddd;
        border-radius: 14px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }}
    .card.hidden {{
        display: none;
    }}
    .image-wrap {{
        background: #eee;
        aspect-ratio: 5 / 7;
        overflow: hidden;
    }}
    img {{
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
    }}
    .content {{
        padding: 14px;
    }}
    .top-line {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 8px;
    }}
    .vendor {{
        color: #555;
        font-size: 12px;
        font-weight: bold;
        margin-top: 10px;
    }}
    h2 {{
        font-size: 15px;
        line-height: 1.35;
        min-height: 42px;
        margin: 6px 0 10px;
    }}
    .status {{
        display: inline-block;
        padding: 4px 9px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: bold;
    }}
    .available {{
        background: #e8f7e8;
        color: #167a2e;
    }}
    .soldout {{
        background: #f7e8e8;
        color: #a82222;
    }}
    .stock-count {{
        font-size: 12px;
        color: #333;
        background: #f0f0ee;
        border-radius: 999px;
        padding: 4px 8px;
        white-space: nowrap;
    }}
    .price {{
        font-weight: bold;
        margin: 8px 0 4px;
    }}
    .compare {{
        color: #777;
        font-size: 13px;
        margin: 0 0 8px;
    }}
    .stock-box {{
        border: 1px solid #e1e1df;
        background: #fafaf8;
        border-radius: 10px;
        padding: 9px;
        margin: 10px 0;
    }}
    .stock-title {{
        font-size: 12px;
        font-weight: bold;
        margin-bottom: 7px;
        color: #333;
    }}
    .variant {{
        display: grid;
        grid-template-columns: 1fr auto;
        gap: 4px 8px;
        align-items: center;
        border-top: 1px solid #e8e8e6;
        padding: 7px 0;
        font-size: 12px;
    }}
    .variant:first-of-type {{
        border-top: 0;
    }}
    .variant-name {{
        line-height: 1.3;
    }}
    .sku {{
        grid-column: 1 / -1;
        color: #888;
        font-size: 11px;
    }}
    .variant-status {{
        border-radius: 999px;
        padding: 3px 7px;
        font-weight: bold;
        white-space: nowrap;
    }}
    .available-variant .variant-status {{
        background: #dcf5dc;
        color: #137225;
    }}
    .soldout-variant {{
        color: #999;
    }}
    .soldout-variant .variant-status {{
        background: #eee;
        color: #777;
    }}
    .date {{
        color: #888;
        font-size: 10px;
        margin: 3px 0;
    }}
    .tags {{
        color: #777;
        font-size: 11px;
        line-height: 1.35;
        min-height: 32px;
    }}
    .button {{
        display: block;
        text-align: center;
        margin-top: 12px;
        padding: 9px 10px;
        border-radius: 8px;
        background: #222;
        color: #fff;
        text-decoration: none;
        font-size: 13px;
    }}
    footer {{
        padding: 24px;
        text-align: center;
        color: #777;
        font-size: 12px;
    }}
</style>
</head>
<body>
<header>
    <h1>THANKS 7DAYS</h1>
    <div class="summary">
        <span>총 상품 {total}개</span>
        <span>재고 상품 {available_products}개</span>
        <span>옵션 재고 {available_variants}/{total_variants}</span>
        <span>품절 옵션 {soldout_variants}개</span>
        <span>마지막 갱신 {now}</span>
        <span>5분 자동 새로고침</span>
    </div>
    <div class="toolbar">
        <button class="brand-toggle" id="brandToggle">브랜드로 필터링 ▾</button>
    </div>
    <div class="brand-panel" id="brandPanel">
        {brand_buttons}
    </div>
    <div class="current-filter" id="currentFilter">전체 브랜드 보기 · {total}개</div>
    <div class="source">
        Source: <a href="{html.escape(COLLECTION_PAGE_URL)}" target="_blank" rel="noopener">THANKS 7DAYS collection</a>
    </div>
</header>
<main class="grid" id="grid">
    {''.join(cards)}
</main>
<footer>
    Generated from public products.json. Pages are fetched until empty.
</footer>
<script>
    const brandCounts = JSON.parse("{brand_counts_json}".replaceAll("&quot;", '"'));
    const cards = Array.from(document.querySelectorAll(".card"));
    const buttons = Array.from(document.querySelectorAll(".brand-button"));
    const panel = document.getElementById("brandPanel");
    const toggle = document.getElementById("brandToggle");
    const currentFilter = document.getElementById("currentFilter");

    toggle.addEventListener("click", () => {{
        panel.classList.toggle("open");
    }});

    function applyBrandFilter(brand) {{
        let visible = 0;

        cards.forEach(card => {{
            const match = brand === "ALL" || card.dataset.brand === brand;
            card.classList.toggle("hidden", !match);
            if (match) visible += 1;
        }});

        buttons.forEach(btn => {{
            btn.classList.toggle("active", btn.dataset.brand === brand);
        }});

        if (brand === "ALL") {{
            currentFilter.textContent = `전체 브랜드 보기 · ${{visible}}개`;
        }} else {{
            currentFilter.textContent = `${{brand}} · ${{visible}}개`;
        }}

        panel.classList.remove("open");
        window.scrollTo({{ top: 0, behavior: "smooth" }});
    }}

    buttons.forEach(btn => {{
        btn.addEventListener("click", () => {{
            applyBrandFilter(btn.dataset.brand);
        }});
    }});
</script>
</body>
</html>
"""


def main():
    products = fetch_all_products()
    page = build_html(products)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(page)

    total_variants = sum(len(p.get("variants") or []) for p in products)
    available_variants = sum(stock_counts(p)[0] for p in products)
    print(
        f"Generated {OUTPUT_FILE} with {len(products)} products, "
        f"{available_variants}/{total_variants} available variants."
    )


if __name__ == "__main__":
    main()
