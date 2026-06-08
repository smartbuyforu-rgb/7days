# 7days

THANKS 7DAYS catalog generator for GitHub Pages.

## This version

- Fetches all pages from `products.json`, not only page 1
- Uses 250 products per page
- Stops when an empty page appears
- Shows product stock and variant-level stock
- Auto-updates every 5 minutes with GitHub Actions
- Page auto-refreshes every 5 minutes in the browser

## Files

- `thanks_7days_catalog_generator.py`: creates `index.html`
- `.github/workflows/update.yml`: updates the catalog every 5 minutes
- `index.html`: generated automatically by GitHub Actions

## How to use

1. Upload all files/folders to the GitHub repository.
2. Go to Actions → Update Thanks Catalog → Run workflow.
3. After success, check that `index.html` exists.
4. Turn on GitHub Pages with branch `main` and folder `/root`.
