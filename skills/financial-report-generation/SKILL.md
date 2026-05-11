---
name: financial-report-generation
category: devops
description: Generate comprehensive weekly financial reports from ledger-web database with interactive Chart.js visualizations
---

# Financial Report Generation Skill

Skill for generating comprehensive weekly financial reports from the ledger-web database on acerserver.

## Overview

Generates interactive HTML reports with Chart.js visualizations showing income, expenses, savings, category breakdowns, recurring expenses, and merchant analysis.

## Prerequisites

- Ledger-web container must be running on acerserver
- SQLite database at /data/finance.db inside ledger-web container
- Access via Docker exec

## Data Source Location

```
Docker Container: ledger-web
Database Path: /data/finance.db
Table: ledger_clean
```

## Data Schema

### Required Columns
| Column Index | Name | Type | Description |
|-------------|------|------|-------------|
| 0 | effective_date | TEXT | Transaction date (YYYY-MM-DD) |
| 1 | merchant | TEXT | Merchant or source name |
| 2 | category | TEXT | Expense/income category |
| 3 | amount | REAL | Transaction amount |
| 4 | direction | TEXT | 'inflow' or 'outflow' |
| 5 | txn_type | TEXT | Transaction type ('purchase', 'transfer', 'payment', 'paycheck', etc.) |

### Key Business Logic

**Expense Classification:**
- Expenses: `direction='outflow' AND txn_type='purchase'`
- Refunds: `direction='inflow' AND txn_type='expense'`
- Transfers: `txn_type IN ('transfer', 'Internal') OR merchant LIKE 'Transfer%'`

## Workflow

### 1. Fetch Transaction Data

```bash
docker exec ledger-web sqlite3 /data/finance.db "
SELECT 
    effective_date as date,
    merchant,
    category,
    amount,
    direction,
    txn_type
FROM ledger_clean
WHERE effective_date >= '2026-01-01'
  AND effective_date <= CURRENT_DATE
ORDER BY effective_date DESC;
"
```

### 2. Parse and Categorize Transactions

Parse pipe-delimited output and classify:
- Income: `direction='inflow'` (excluding refunds)
- Expenses: `direction='outflow' AND txn_type='purchase'`
- Refunds: `direction='inflow' AND txn_type='expense'`
- Transfers: Exclude from financial analysis

### 3. Calculate Financial Metrics

```python
total_income = sum(tx['amount'] for tx in income)
total_expenses = sum(tx['amount'] for tx in expenses)
total_refunds = sum(tx['amount'] for tx in refunds)
net_spend = total_expenses - total_refunds
savings = total_income - total_expenses + total_refunds
```

### 4. Generate Category Analysis

Group by category and calculate:
- Total spend per category
- Monthly breakdown per category
- Average spend across months

### 5. Generate Recurring Expense Patterns

Identify recurring patterns:
- Group by merchant + category + rounded amount
- Filter for transactions on different dates (count ≥ 2)
- Sort by total amount

### 6. Build HTML Report

Create interactive HTML with Chart.js:
- Summary cards (income/expenses/savings)
- Monthly income vs expenses bar chart
- Net spending by category horizontal bar chart
- Category breakdown doughnut chart (top 8)
- Monthly category heatmap
- Income sources chart
- Top 15 merchants table
- Key insights box
- Recurring expenses list

## HTML Report Structure

### CSS Requirements
- Dark theme: `#0f1117` background, `#1a1d27` cards
- Color scheme: Green (#4ade80) for positive, Red (#f87171) for negative, Blue (#60a5fa) for neutral
- Zero border-radius anywhere (sharp corners only)
- Mobile responsive with media queries

### Chart.js Integration
- Load from CDN: `https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js`
- Use responsive: true
- Dark theme colors for text and grid lines
- Custom callbacks for currency formatting in tick labels

### Data Templates

#### Summary Cards
```javascript
const summary = {
    income: 90885.41,
    expenses: 32501.94,
    net: 32501.94,
    savings: 58383.47
};
```

#### Monthly Chart
Bar chart showing three datasets: Income (green), Expenses (red), Net (blue)

#### Category Charts
- Horizontal bar chart: top 12 categories by net spend
- Doughnut chart: top 8 categories by expense amount

#### Income Sources Chart
Bar chart showing top 5 income sources

#### Merchants Table
Top 15 merchants sorted by spending amount

#### Recurring Expenses
List of 5-10 highest-value recurring patterns with:
- Average amount
- Total amount across occurrences
- Count of occurrences

## Example Output File

```bash
/tmp/finance_report_2026.html
```

After generating, publish it for Chris to open from Telegram:

```python
from agent.published_artifacts import publish_artifact

url = publish_artifact(
    "/tmp/finance_report_2026.html",
    display_name="finance_report_2026.html"
)
# Send to Chris: f"Financial report: [finance_report_2026.html]({url})"
```

## Common Issues and Solutions

### Issue: Container not found
**Solution:** The finance data is in `ledger-web` container, not a separate finance-hub-db container

### Issue: Wrong data format
**Solution:** Data is pipe-delimited (`|`), not comma-delimited. 6 columns in query result.

### Issue: No expenses showing
**Solution:** Expenses are identified by `direction='outflow' AND txn_type='purchase'`, not `txn_type='expense'`

### Issue: Wrong transaction types
**Solution:** Payment transactions (CC payments, mortgage) have `txn_type='payment'`, not 'purchase'

## Time Range Parameters

### Weekly Report
```sql
WHERE effective_date >= '2026-01-01' AND effective_date <= CURRENT_DATE
```

### Monthly Report
```sql
WHERE effective_date >= '2026-01-01' AND effective_date <= DATE('2026-01-31')
```

### Quarterly Report
```sql
WHERE effective_date >= '2026-01-01' AND effective_date <= DATE('2026-03-31')
```

## Customization Options

### Adjust Category Limits
Modify chart data arrays to show different numbers of categories (e.g., top 10 instead of top 8)

### Add Additional Charts
Append new Chart.js initialization blocks for custom visualizations

### Custom Theme
Modify CSS color variables in the style section

## Data Validation

Always verify:
1. Total income = sum of all income transactions
2. Total expenses = sum of all expense transactions
3. Savings = Income - Expenses + Refunds
4. Net spend = Expenses - Refunds
5. Recurring patterns make financial sense

## Reporting Frequency

Use this skill to generate:
- Weekly reports (date range to today)
- Monthly reports (date range for calendar month)
- Quarterly reports (date range for quarter)
- Year-to-date reports (date range from Jan 1)

## Dependencies

- Docker CLI installed on acerserver
- SQLite3 client (via docker exec)
- Python 3 with json module
- Chart.js 4.4.7 CDN
- Local storage for temporary HTML file

## Author

Generated for acerserver operations (Chris Pack)

## Last Updated

2026-05-03