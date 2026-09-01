# Empower API Reference — Verified 2026-06-21

Source: `http://localhost:8610` (Empower FastAPI service, localhost only)

## Health
```
GET /health
→ { status: "ok", service: "empower", version: "master@<sha>", transaction_count: N,
    account_count: N, open_issues: N, unclassified: N, unlinked_card_payments: N }
```

## Dashboard Summary
```
GET /api/dashboard/summary
→ {
    total_income: 90870.81,
    total_expenses: 96529.33,
    direct_spend: 54905.37,
    debt_service: 24637.98,
    loans: 16985.98,
    net: 1605.07,
    avg_monthly_spend: 13789.90,
    month_count: 7
  }
```

## Spending by Merchant
```
GET /api/spending/merchants
→ { scope: "month", items: [{ merchant, count, total, date_from, date_to }, ...] }
```

## Transactions
```
GET /api/transactions?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
→ [{ id, effective_date, merchant_clean, amount, direction, category,
     parent_category, is_transfer, transaction_class, needs_review }, ...]
```

## Categories
```
GET /api/categories
→ [{ name, slug, parent_slug, color }, ...]
```

## Planning Summary (Recurring)
```
GET /api/planning/summary
→ { recurring: [{ name, amount, cadence, next_date }, ...] }
```

## IMPORTANT
- `/reports/monthly?month=YYYY-MM` returns SPA HTML shell — NOT JSON API
- Do NOT use `finance-hub-db` (Postgres) — NOT source of truth
- Do NOT use old `generate_financial_report.py` — wrong DB path
