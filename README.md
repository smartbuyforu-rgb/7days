# 7days

THANKS 7DAYS catalog generator for GitHub Pages.

## What changed

This version shows stock more clearly.

- Product stock badge
- Available variant count
- Sold out variant count
- Variant-level stock list
- Auto update every 5 minutes

## Files

- `thanks_7days_catalog_generator.py`: creates `index.html`
- `.github/workflows/update.yml`: updates the catalog every 5 minutes
- `index.html`: generated automatically by GitHub Actions

## How to use

1. Upload all files/folders to the GitHub repository.
2. Go to Actions → Update Thanks Catalog → Run workflow.
3. After success, check that `index.html` exists.
4. Turn on GitHub Pages with branch `main` and folder `/root`.
