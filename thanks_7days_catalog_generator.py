import html
from datetime import datetime, timezone, timedelta

import requests

COLLECTION_JSON_URL = "https://www.isseymiyake.com/collections/thanks-7days/products.json?limit=250&page=1"
PRODUCT_BASE_URL = "https://www.isseymiyake.com/products/"
OUTPUT_FILE = "index.html"


def yen(value):
    try:
        return f"{int(value):,}円"
    except Exception:
        return "-"


def fetch_products():
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json,text/plain,*/*",
    }
    response = requests.get(COLLECTION_JSON_URL, headers=headers, timeout=20)
    response.raise_for_status()
    data = response.json()
    return data.get("products", [])


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


def build_html(products):
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S JST")

    cards = []

    for product in products:
        title = html.escape(product.get("title", "No title"))
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

        status_class = "available" if available else "soldout"
        status_text = "재고 있음" if available else "전체 품절"

        variant_stock_html = build_variant_stock_html(product)

        card = f"""
        <article class="card">
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
                <h2>{title}</h2>
                <p class="price">가격: {price}</p>
                <p class="compare">정상가: {compare_price}</p>

                <div class="stock-box">
                    <div class="stock-title">옵션별 재고</div>
                    {variant_stock_html}
                </div>

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

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
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
        z-index: 10;
        background: rgba(255,255,255,0.95);
        border-bottom: 1px solid #ddd;
        padding: 18px 24px;
        backdrop-filter: blur(8px);
    }}
    h1 {{
        margin: 0 0 8px;
        font-size: 24px;
    }}
    .summary {{
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        font-size: 13px;
        color: #444;
    }}
    .summary span {{
        background: #fff;
        border: 1px solid #ddd;
        border-radius: 999px;
        padding: 5px 10px;
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
    h2 {{
        font-size: 15px;
        line-height: 1.35;
        min-height: 42px;
        margin: 10px 0;
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
    <h1>THANKS 7DAYS Catalog</h1>
    <div class="summary">
        <span>총 상품 {total}개</span>
        <span>재고 상품 {available_products}개</span>
        <span>옵션 재고 {available_variants}/{total_variants}</span>
        <span>품절 옵션 {soldout_variants}개</span>
        <span>마지막 업데이트 {now}</span>
    </div>
</header>
<main class="grid">
    {''.join(cards)}
</main>
<footer>
    Generated from public products.json
</footer>
</body>
</html>
"""


def main():
    products = fetch_products()
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
