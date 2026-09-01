#!/usr/bin/env python3
"""
Financial Report Generator

Generates comprehensive financial reports from ledger-web database.
Usage: python3 generate_financial_report.py [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD]

The report is written to /tmp/finance_report_<date>.html
"""

import sqlite3
import json
import argparse
from datetime import datetime, timedelta
from collections import defaultdict


def get_transactions(start_date, end_date):
    """Query transactions from ledger_web database."""
    conn = sqlite3.connect('/home/chris/docker/ledger/data/finance.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = """
    SELECT 
        effective_date as date,
        merchant,
        category,
        amount,
        direction,
        txn_type
    FROM ledger_clean
    WHERE effective_date >= ? 
      AND effective_date <= ?
    ORDER BY effective_date DESC;
    """

    cursor.execute(query, (start_date, end_date))
    transactions = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return transactions


def categorize_transactions(transactions):
    """Categorize transactions by type."""
    income = []
    expenses = []
    refunds = []
    transfers = []

    for tx in transactions:
        # Check for transfers first
        if tx['txn_type'] in ['transfer', 'Internal'] or str(tx['merchant']).startswith('Transfer'):
            transfers.append(tx)
        # Check for refunds
        elif tx['direction'] == 'inflow' and tx['txn_type'] == 'expense':
            refunds.append(tx)
        # Check for income
        elif tx['direction'] == 'inflow':
            income.append(tx)
        # Check for expenses
        elif tx['direction'] == 'outflow' and tx['txn_type'] == 'purchase':
            expenses.append(tx)
        # Other outflows
        elif tx['direction'] == 'outflow':
            # Add to hidden/expenses as needed
            expenses.append(tx)

    return income, expenses, refunds, transfers


def calculate_metrics(income, expenses, refunds):
    """Calculate financial metrics."""
    total_income = sum(tx['amount'] for tx in income)
    total_expenses = sum(tx['amount'] for tx in expenses)
    total_refunds = sum(tx['amount'] for tx in refunds)
    net_spend = total_expenses - total_refunds
    savings = total_income - total_expenses + total_refunds

    return {
        'total_income': total_income,
        'total_expenses': total_expenses,
        'total_refunds': total_refunds,
        'net_spend': net_spend,
        'savings': savings
    }


def analyze_categories(expenses, refunds):
    """Analyze spending by category."""
    category_spend = defaultdict(lambda: {'total': 0.0, 'expenses': 0.0, 'refunds': 0.0, 'monthly': defaultdict(float)})

    for tx in expenses:
        cat = tx['category'] or 'Uncategorized'
        category_spend[cat]['total'] += tx['amount']
        category_spend[cat]['expenses'] += tx['amount']

        month_key = tx['date'][:7]
        category_spend[cat]['monthly'][month_key] += tx['amount']

    for tx in refunds:
        cat = tx['category'] or 'Uncategorized'
        category_spend[cat]['total'] += tx['amount']
        category_spend[cat]['refunds'] += tx['amount']

    # Filter to actual spend
    actual_category_spend = {cat: data for cat, data in category_spend.items() if data['expenses'] > 0}
    sorted_categories = sorted(actual_category_spend.items(), key=lambda x: x[1]['total'], reverse=True)

    return sorted_categories


def analyze_merchants(expenses):
    """Analyze spending by merchant."""
    merchant_spend = defaultdict(float)

    for tx in expenses:
        merch = tx['merchant'] or 'Unknown'
        merchant_spend[merch] += tx['amount']

    sorted_merchants = sorted(merchant_spend.items(), key=lambda x: x[1], reverse=True)

    return sorted_merchants


def analyze_monthly(expenses, income):
    """Analyze monthly breakdown."""
    monthly_data = defaultdict(lambda: {'income': 0.0, 'expenses': 0.0, 'net': 0.0})
    monthly_spend_by_cat = defaultdict(lambda: defaultdict(float))

    for tx in expenses:
        month_key = tx['date'][:7]
        monthly_data[month_key]['expenses'] += tx['amount']
        monthly_spend_by_cat[month_key][tx['category']] += tx['amount']

    for tx in income:
        month_key = tx['date'][:7]
        monthly_data[month_key]['income'] += tx['amount']

    month_names = sorted(monthly_data.keys())
    income_vals = [monthly_data[m]['income'] for m in month_names]
    expense_vals = [monthly_data[m]['expenses'] for m in month_names]
    net_vals = [monthly_data[m]['income'] - monthly_data[m]['expenses'] for m in month_names]

    avg_monthly_spend = sum(expense_vals) / len(expense_vals) if expense_vals else 0
    avg_monthly_income = sum(income_vals) / len(income_vals) if income_vals else 0

    return {
        'labels': month_names,
        'income': income_vals,
        'expenses': expense_vals,
        'net': net_vals,
        'avg_monthly_income': avg_monthly_income,
        'avg_monthly_spend': avg_monthly_spend
    }


def analyze_recurring(expenses):
    """Identify recurring expense patterns."""
    tx_pattern = defaultdict(list)

    for tx in expenses:
        pattern = f"{tx['merchant']}|{tx['category']}|{round(tx['amount'])}"
        tx_pattern[pattern].append(tx)

    recurring = []

    for pattern, tx_list in tx_pattern.items():
        if len(tx_list) >= 2:
            dates = sorted([tx['date'] for tx in tx_list])
            if len(set(dates)) >= 2:
                total = sum(tx['amount'] for tx in tx_list)
                avg = total / len(tx_list)
                recurring.append({
                    'pattern': pattern,
                    'count': len(tx_list),
                    'total': total,
                    'average': avg,
                    'transactions': tx_list[:3]
                })

    recurring.sort(key=lambda x: x['total'], reverse=True)

    return recurring[:10]


def generate_html_report(data, output_path):
    """Generate HTML report from data."""
    # Generate insights
    insights = [
        f"Savings Rate: {data['summary']['savings'] / data['summary']['total_income'] * 100:.1f}% of income was saved this period",
        f"Top Spending Category: {data['categories']['by_spend'][0][0] if data['categories']['by_spend'] else 'N/A'} at ${data['categories']['by_spend'][0][1]['expenses']:.2f}",
        f"Monthly Average: Income ${data['summary']['avg_monthly_income']:.2f}, Expenses ${data['summary']['avg_monthly_spend']:.2f}"
    ]

    # Generate recurring HTML
    recurring_html = ''
    for item in data['recurring'][:5]:
        recurring_html += f'''
        <div class="recurring-item">
            <div class="recurring-header">
                <span>{item['pattern'].split('|')[0] if '|' in item['pattern'] else item['pattern']}</span>
                <span>${item['average']:.2f} avg</span>
            </div>
            <div class="recurring-details">
                <span>Total: ${item['total']:.2f}</span>
                <span class="recurring-count">{item['count']} occurrences</span>
            </div>
        </div>
        '''

    # Prepare merchants data for charts
    merchants_data = [[merch[0], merch[1], cat] for merch, cat in [(m, 'Uncategorized') for m in data['merchants']]]

    # Format data for JSON serialization
    category_data = []
    for cat, data_cat in data['categories']['by_spend'][:12]:
        category_data.append({
            'category': cat,
            'expenses': data_cat['expenses'],
            'refunds': data_cat['refunds']
        })

    income_sources = []
    for source in data['income_sources'][:5]:
        income_sources.append({
            'source': source[0],
            'amount': source[1]
        })

    recurring_data = []
    for item in data['recurring']:
        recurring_data.append({
            'name': item['pattern'].split('|')[0] if '|' in item['pattern'] else item['pattern'],
            'count': item['count'],
            'average': item['average'],
            'total': item['total']
        })

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Financial Report - Chris Pack</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            background-color: #0f1117;
            color: #ffffff;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        h1 {{
            font-size: 2rem;
            margin-bottom: 20px;
            color: #ffffff;
        }}

        h2 {{
            font-size: 1.5rem;
            margin-top: 30px;
            margin-bottom: 15px;
            color: #ffffff;
            border-bottom: 2px solid #1a1d27;
            padding-bottom: 10px;
        }}

        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .card {{
            background-color: #1a1d27;
            padding: 20px;
            border: 1px solid #2a2d35;
        }}

        .card-label {{
            font-size: 0.9rem;
            color: #888;
            margin-bottom: 10px;
        }}

        .card-value {{
            font-size: 1.8rem;
            font-weight: bold;
        }}

        .card-value.positive {{ color: #4ade80; }}
        .card-value.negative {{ color: #f87171; }}
        .card-value.neutral {{ color: #60a5fa; }}

        .chart-wrapper {{
            background-color: #1a1d27;
            padding: 20px;
            border: 1px solid #2a2d35;
            margin-bottom: 30px;
        }}

        canvas {{
            max-width: 100%;
        }}

        .table-wrapper {{
            overflow-x: auto;
            background-color: #1a1d27;
            border: 1px solid #2a2d35;
            margin-bottom: 30px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }}

        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #2a2d35;
        }}

        th {{
            background-color: #252833;
            font-weight: 600;
            color: #ffffff;
            position: sticky;
            top: 0;
        }}

        tr:hover {{
            background-color: #252833;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Financial Report</h1>
        <div style="text-align: center; color: #888; margin-bottom: 30px; font-size: 0.9rem;">
            {data['date_range']}
        </div>

        <div class="summary-grid">
            <div class="card">
                <div class="card-label">Total Income</div>
                <div class="card-value positive">${data['summary']['total_income']:,.2f}</div>
            </div>
            <div class="card">
                <div class="card-label">Total Expenses</div>
                <div class="card-value negative">${data['summary']['total_expenses']:,.2f}</div>
            </div>
            <div class="card">
                <div class="card-label">Net Spending</div>
                <div class="card-value neutral">${data['summary']['net_spend']:,.2f}</div>
            </div>
            <div class="card">
                <div class="card-label">Savings</div>
                <div class="card-value positive">${data['summary']['savings']:,.2f}</div>
            </div>
        </div>

        <div class="chart-wrapper">
            <h2>Monthly Income vs Expenses</h2>
            <canvas id="monthlyChart"></canvas>
        </div>

        <div class="chart-wrapper">
            <h2>Net Spending by Category (Top 8)</h2>
            <canvas id="categoryChart"></canvas>
        </div>

        <div class="chart-wrapper">
            <h2>Income Sources (Top 5)</h2>
            <canvas id="incomeChart"></canvas>
        </div>

        <div class="chart-wrapper">
            <h2>Top 15 Merchants</h2>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Merchant</th>
                            <th>Amount</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join([f"<tr><td>{m[0]}</td><td>${m[1]:,.2f}</td></tr>" for m in data['merchants']])}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        const monthlyData = {{ 
            labels: {json.dumps(data['monthly']['labels'])},
            income: {json.dumps(data['monthly']['income'])},
            expenses: {json.dumps(data['monthly']['expenses'])},
            net: {json.dumps(data['monthly']['net'])}
        }};

        const categoryData = {json.dumps(category_data)};

        const incomeSources = {json.dumps(income_sources)};

        const merchants = {json.dumps(merchants_data)};

        new Chart(document.getElementById('monthlyChart'), {{
            type: 'bar',
            data: {{
                labels: monthlyData.labels,
                datasets: [{{
                    label: 'Income',
                    data: monthlyData.income,
                    backgroundColor: '#4ade80',
                    borderColor: '#4ade80',
                    borderWidth: 1
                }}, {{
                    label: 'Expenses',
                    data: monthlyData.expenses,
                    backgroundColor: '#f87171',
                    borderColor: '#f87171',
                    borderWidth: 1
                }}, {{
                    label: 'Net',
                    data: monthlyData.net,
                    backgroundColor: '#60a5fa',
                    borderColor: '#60a5fa',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            callback: function(value) {{
                                return '$' + value.toLocaleString();
                            }}
                        }}
                    }}
                }}
            }}
        }});

        new Chart(document.getElementById('categoryChart'), {{
            type: 'doughnut',
            data: {{
                labels: categoryData.map(d => d.category),
                datasets: [{{
                    data: categoryData.map(d => d.expenses),
                    backgroundColor: ['#f87171', '#60a5fa', '#4ade80', '#fbbf24', '#a78bfa', '#f472b6', '#34d399', '#fb923c'],
                    borderColor: '#1a1d27',
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        position: 'right'
                    }}
                }}
            }}
        }});

        new Chart(document.getElementById('incomeChart'), {{
            type: 'bar',
            data: {{
                labels: incomeSources.map(d => d.source),
                datasets: [{{
                    label: 'Income Amount',
                    data: incomeSources.map(d => d.amount),
                    backgroundColor: '#4ade80',
                    borderColor: '#4ade80',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            callback: function(value) {{
                                return '$' + value.toLocaleString();
                            }}
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""

    with open(output_path, 'w') as f:
        f.write(html)


def main():
    parser = argparse.ArgumentParser(description='Generate financial report from ledger-web database')
    parser.add_argument('--start-date', default='2026-01-01', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', default=datetime.now().strftime('%Y-%m-%d'), help='End date (YYYY-MM-DD)')
    args = parser.parse_args()

    print(f"Fetching transactions from {args.start_date} to {args.end_date}...")

    transactions = get_transactions(args.start_date, args.end_date)
    print(f"Found {len(transactions)} transactions")

    income, expenses, refunds, transfers = categorize_transactions(transactions)

    metrics = calculate_metrics(income, expenses, refunds)
    print(f"\nTotal Income: ${metrics['total_income']:,.2f}")
    print(f"Total Expenses: ${metrics['total_expenses']:,.2f}")
    print(f"Savings: ${metrics['savings']:,.2f}")

    categories = analyze_categories(expenses, refunds)
    merchants = analyze_merchants(expenses)
    monthly = analyze_monthly(expenses, income)
    recurring = analyze_recurring(expenses)

    # Collect income sources
    income_sources = []
    for tx in income:
        income_sources.append((tx['merchant'] or 'Unknown', tx['amount']))

    # Prepare data
    data = {
        'summary': metrics,
        'categories': {
            'by_spend': categories
        },
        'merchants': merchants,
        'monthly': monthly,
        'income_sources': income_sources,
        'recurring': recurring,
        'date_range': f"{args.start_date} to {args.end_date}"
    }

    # Generate output filename
    filename = f"/tmp/finance_report_{datetime.now().strftime('%Y%m%d')}.html"
    generate_html_report(data, filename)

    print(f"\nReport generated: {filename}")


if __name__ == '__main__':
    main()