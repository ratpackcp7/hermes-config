#!/usr/bin/env bash
# Weekly Finance Report — Empower API source-of-truth wrapper.
# Cron invokes this script only; no SQL, no finance-hub-db, no agent-owned business logic.
set -euo pipefail

EMPOWER_API="${EMPOWER_API:-http://localhost:8610}"
OUTPUT_DIR="${HOME}/.hermes/cron/output"
REPORT_DATE="$(date +%Y-%m-%d)"
REPORT_FILE="${OUTPUT_DIR}/weekly-finance-report-${REPORT_DATE}.html"
LOG_FILE="${OUTPUT_DIR}/weekly-finance-report.log"

mkdir -p "$OUTPUT_DIR"

log() {
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

die() {
  log "ERROR: $*"
  echo "WEEKLY_FINANCE_REPORT_FAILED: $*" >&2
  exit 1
}

log "=== Weekly Finance Report (Empower) ==="
log "Empower API: $EMPOWER_API"
log "Report file: $REPORT_FILE"

if ! curl -sf --max-time 10 "${EMPOWER_API}/api/dashboard/summary" >/dev/null 2>&1; then
  die "Empower API unreachable at ${EMPOWER_API}"
fi

python3 - "$EMPOWER_API" "$REPORT_FILE" "$REPORT_DATE" <<'PYEOF'
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

API_BASE, REPORT_FILE, TODAY_STR = sys.argv[1:4]
TODAY = date.fromisoformat(TODAY_STR)
WEEKLY_START = TODAY - timedelta(days=6)
MTD_START = TODAY.replace(day=1)

PERIODS = {
    "weekly": (WEEKLY_START.isoformat(), TODAY.isoformat()),
    "mtd": (MTD_START.isoformat(), TODAY.isoformat()),
}


def fetch_json(path: str, params: dict | None = None) -> dict:
    url = f"{API_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.URLError as exc:
        raise SystemExit(f"Empower API unreachable for {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON from {path}: {exc}") from exc


def money(n: float) -> str:
    return f"${abs(n):,.2f}"


def fmt_signed(n: float) -> str:
    sign = "+" if n >= 0 else "-"
    return f"{sign}{money(n)}"


def fetch_period_bundle(label: str, start: str, end: str) -> dict:
    params = {"start_date": start, "end_date": end}
    summary = fetch_json("/api/dashboard/summary", params)
    spending = fetch_json("/api/spending", params)
    merchants = fetch_json("/api/spending/merchants", params)
    transactions = fetch_json(
        "/api/transactions",
        {**params, "per_page": "50", "sort_by": "effective_date", "sort_dir": "desc"},
    )
    ps = summary.get("period_start")
    pe = summary.get("period_end")
    if ps and pe and (ps != start or pe != end):
        raise SystemExit(
            f"Period mismatch for {label}: requested {start}..{end}, summary returned {ps}..{pe}"
        )
    return {
        "label": label,
        "start": start,
        "end": end,
        "summary": summary,
        "spending": spending,
        "merchants": merchants,
        "transactions": transactions,
    }


weekly = fetch_period_bundle("weekly", *PERIODS["weekly"])
mtd = fetch_period_bundle("mtd", *PERIODS["mtd"])

period_meta = {
    "report_date": TODAY_STR,
    "weekly_start": PERIODS["weekly"][0],
    "weekly_end": PERIODS["weekly"][1],
    "mtd_start": PERIODS["mtd"][0],
    "mtd_end": PERIODS["mtd"][1],
    "source": "empower-api",
    "api_base": API_BASE,
}


def category_rows(spending: dict) -> list[tuple[str, float, int]]:
    rows: list[tuple[str, float, int]] = []
    for month in spending.get("months", []):
        for cat in month.get("categories", []):
            rows.append(
                (
                    cat.get("display") or cat.get("parent_category", "?"),
                    cat.get("total", 0),
                    cat.get("count", 0),
                )
            )
    rows.sort(key=lambda r: abs(r[1]), reverse=True)
    return rows


def merchant_rows(merchants: dict, limit: int = 15) -> list[dict]:
    items = merchants.get("items", [])
    items = sorted(items, key=lambda m: abs(m.get("total", 0)), reverse=True)
    return items[:limit]


def txn_rows(transactions: dict, limit: int = 25) -> list[dict]:
    return transactions.get("items", [])[:limit]


def section_cards(summary: dict) -> str:
    net = summary.get("net", 0)
    net_class = "pos" if net >= 0 else "neg"
    return f"""
    <div class="cards">
      <div class="card"><div class="label">Income</div><div class="value">{money(summary.get('total_income', 0))}</div></div>
      <div class="card"><div class="label">Expenses</div><div class="value">{money(summary.get('total_expenses', 0))}</div></div>
      <div class="card"><div class="label">Direct Spend</div><div class="value">{money(summary.get('direct_spend', 0))}</div></div>
      <div class="card"><div class="label">Debt Service</div><div class="value">{money(summary.get('debt_service', 0))}</div></div>
      <div class="card"><div class="label">Loans</div><div class="value">{money(summary.get('loans', 0))}</div></div>
      <div class="card"><div class="label">Net</div><div class="value {net_class}">{fmt_signed(net)}</div></div>
    </div>
    """


def table_categories(rows: list[tuple[str, float, int]]) -> str:
    if not rows:
        return "<p class='muted'>No category spending in period.</p>"
    body = "".join(
        f"<tr><td>{name}</td><td class='num'>{fmt_signed(total)}</td><td class='num'>{count}</td></tr>"
        for name, total, count in rows
    )
    return f"<table><thead><tr><th>Category</th><th>Total</th><th>Txns</th></tr></thead><tbody>{body}</tbody></table>"


def table_merchants(items: list[dict]) -> str:
    if not items:
        return "<p class='muted'>No merchant spending in period.</p>"
    body = "".join(
        f"<tr><td>{m.get('merchant', '?')}</td><td class='num'>{fmt_signed(m.get('total', 0))}</td><td class='num'>{m.get('count', 0)}</td></tr>"
        for m in items
    )
    return f"<table><thead><tr><th>Merchant</th><th>Total</th><th>Txns</th></tr></thead><tbody>{body}</tbody></table>"


def table_transactions(items: list[dict]) -> str:
    if not items:
        return "<p class='muted'>No transactions in period.</p>"
    body = "".join(
        f"<tr><td>{t.get('effective_date','')}</td><td>{t.get('merchant_clean') or t.get('merchant_raw','?')}</td>"
        f"<td>{t.get('category','')}</td><td class='num'>{fmt_signed(t.get('amount', 0))}</td></tr>"
        for t in items
    )
    return f"<table><thead><tr><th>Date</th><th>Merchant</th><th>Category</th><th>Amount</th></tr></thead><tbody>{body}</tbody></table>"


def period_section(bundle: dict) -> str:
    return f"""
    <section>
      <h2>{bundle['label'].upper()} — {bundle['start']} to {bundle['end']}</h2>
      {section_cards(bundle['summary'])}
      <h3>Spending by Category</h3>
      {table_categories(category_rows(bundle['spending']))}
      <h3>Top Merchants</h3>
      {table_merchants(merchant_rows(bundle['merchants']))}
      <h3>Recent Transactions</h3>
      {table_transactions(txn_rows(bundle['transactions']))}
    </section>
    """


meta_json = json.dumps(period_meta, separators=(",", ":"))


def _safe_rate(net, income):
    try:
        income = float(income)
        net = float(net)
        if income == 0:
            return "N/A"
        return f"{(net / income) * 100:.1f}%"
    except (TypeError, ValueError):
        return "N/A"


def _month_count(start_str, end_str):
    try:
        from datetime import date
        s = date.fromisoformat(start_str)
        e = date.fromisoformat(end_str)
        return max(1, (e.year - s.year) * 12 + (e.month - s.month) + 1)
    except Exception:
        return 1


def mtd_banner(mtd):
    s = mtd["summary"]
    net_class = "positive" if (s.get("net", 0) or 0) >= 0 else "negative"
    return f"""
    <h2>Month-to-Date Context — {mtd['start']} to {mtd['end']}</h2>
    <div class="cards">
      <div class="card"><div class="label">Income</div><div class="value positive">{money(s.get('total_income', 0))}</div></div>
      <div class="card"><div class="label">Expenses</div><div class="value negative">{money(s.get('total_expenses', 0))}</div></div>
      <div class="card"><div class="label">Net</div><div class="value {net_class}">{fmt_signed(s.get('net', 0))}</div></div>
      <div class="card"><div class="label">Avg Monthly Spend</div><div class="value neutral">{money(s.get('avg_monthly_spend', 0))}</div></div>
      <div class="card"><div class="label">Savings Rate</div><div class="value {net_class}">{_safe_rate(s.get('net', 0), s.get('total_income', 0))}</div></div>
    </div>
    <div class="callout{'success' if (s.get('net',0) or 0) >= 0 else 'warning'}">
      <strong>MTD insight:</strong> {_month_count(mtd['start'], mtd['end'])} month(s) · Income {money(s.get('total_income', 0))} · Expenses {money(s.get('total_expenses', 0))} · Net {fmt_signed(s.get('net', 0))}
    </div>"""


def build_report_html(PERIODS, weekly, mtd, meta_json, API_BASE, TODAY_STR):
    """Build full HTML report matching original CP7 finance report style."""
    w_summary = weekly["summary"]
    m_summary = mtd["summary"]

    w_income = money(w_summary.get("total_income", 0))
    w_expenses = money(w_summary.get("total_expenses", 0))
    w_net = fmt_signed(w_summary.get("net", 0))
    w_savings_rate = _safe_rate(w_summary.get("net", 0), w_summary.get("total_income", 0))
    w_months = _month_count(PERIODS["weekly"][0], PERIODS["weekly"][1])
    w_avg = money(abs(w_summary.get("total_expenses", 0)) / w_months) if w_months else "$0.00"

    m_income = money(m_summary.get("total_income", 0))
    m_expenses = money(m_summary.get("total_expenses", 0))
    m_net = fmt_signed(m_summary.get("net", 0))
    m_savings_rate = _safe_rate(m_summary.get("net", 0), m_summary.get("total_income", 0))
    m_months = _month_count(PERIODS["mtd"][0], PERIODS["mtd"][1])
    m_avg = money(abs(m_summary.get("total_expenses", 0)) / m_months) if m_months else "$0.00"

    w_net_class = "positive" if (w_summary.get("net", 0) or 0) >= 0 else "negative"
    m_net_class = "positive" if (m_summary.get("net", 0) or 0) >= 0 else "negative"

    def period_html(bundle, period_key):
        s = bundle["summary"]
        label = bundle["label"]
        start = bundle["start"]
        end = bundle["end"]
        net_class = "positive" if (s.get("net", 0) or 0) >= 0 else "negative"
        income = money(s.get("total_income", 0))
        expenses = money(s.get("total_expenses", 0))
        net = fmt_signed(s.get("net", 0))
        direct = money(s.get("direct_spend", 0))
        debt = money(s.get("debt_service", 0))
        loans = money(s.get("loans", 0))
        months = _month_count(start, end)
        avg = money(abs(s.get("total_expenses", 0)) / months) if months else "$0.00"
        rate = _safe_rate(s.get("net", 0), s.get("total_income", 0))

        cats = category_rows(bundle["spending"])
        cats_html = table_categories(cats[:12]) if cats else "<p class='muted'>No category spending in period.</p>"

        merch = merchant_rows(bundle["merchants"], 15)
        merch_html = table_merchants(merch) if merch else "<p class='muted'>No merchant spending in period.</p>"

        txns = txn_rows(bundle["transactions"], 5)
        txn_html = table_transactions(txns) if txns else "<p class='muted'>No transactions in period.</p>"

        return f"""
    <h2>{label} — {start} to {end}</h2>
    <div class="cards">
      <div class="card"><div class="label">Income</div><div class="value positive">{income}</div></div>
      <div class="card"><div class="label">Expenses</div><div class="value negative">{expenses}</div></div>
      <div class="card"><div class="label">Net</div><div class="value {net_class}">{net}</div></div>
      <div class="card"><div class="label">Direct Spend</div><div class="value neutral">{direct}</div></div>
      <div class="card"><div class="label">Debt Service</div><div class="value neutral">{debt}</div></div>
      <div class="card"><div class="label">Loans</div><div class="value neutral">{loans}</div></div>
      <div class="card"><div class="label">Avg Monthly Spend</div><div class="value neutral">{avg}</div></div>
      <div class="card"><div class="label">Savings Rate</div><div class="value {net_class}">{rate}</div></div>
    </div>
    <div class="callout{'success' if (s.get('net',0) or 0) >= 0 else 'warning'}">
      <strong>{label} insight:</strong> {months} month(s) · Income {income} · Expenses {expenses} · Net {net} · Savings rate {rate}
    </div>
    <h3>Spending by Category</h3>
    {cats_html}
    <h3>Top Merchants</h3>
    {merch_html}
    <h3>Recent Transactions</h3>
    {txn_html}"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Weekly Finance Report — {TODAY_STR}</title>
  <meta name="PERIOD_META" content='{meta_json}'>
  <!-- PERIOD_META {meta_json} -->
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; border-radius: 0 !important; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f1117; color: #e1e4e8; padding: 16px; }}
    h1 {{ font-size: 1.5rem; margin-bottom: 4px; color: #f0f3f6; }}
    h2 {{ font-size: 1.1rem; margin: 20px 0 10px; color: #f0f3f6; border-bottom: 1px solid #21262d; padding-bottom: 6px; }}
    h3 {{ font-size: 1rem; margin: 16px 0 8px; color: #f0f3f6; }}
    .subtitle {{ color: #8b949e; font-size: 0.85rem; margin-bottom: 20px; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 20px; }}
    .card {{ background: #1a1d27; border: 1px solid #21262d; padding: 14px; }}
    .card .label {{ color: #8b949e; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; }}
    .card .value {{ font-size: 1.4rem; font-weight: 700; margin-top: 4px; }}
    .positive {{ color: #3fb950; }}
    .negative {{ color: #f85149; }}
    .neutral {{ color: #e1e4e8; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; background: #1a1d27; border: 1px solid #21262d; }}
    th {{ background: #161b22; color: #8b949e; font-size: 0.75rem; text-transform: uppercase; padding: 8px 10px; text-align: left; border-bottom: 1px solid #21262d; }}
    td {{ padding: 7px 10px; border-bottom: 1px solid #21262d; font-size: 0.85rem; }}
    tr:last-child td {{ border-bottom: none; }}
    td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .callout {{ background: #1a1d27; border: 1px solid #21262d; border-left: 3px solid #58a6ff; padding: 10px 14px; margin-bottom: 12px; font-size: 0.85rem; }}
    .callout.warning {{ border-left-color: #d29922; }}
    .callout.success {{ border-left-color: #3fb950; }}
    footer {{ margin-top: 24px; color: #8b949e; font-size: 0.8rem; }}
    @media (max-width: 600px) {{ .cards {{ grid-template-columns: 1fr 1fr; }} }}
  </style>
</head>
<body>
<h1>Weekly Finance Report</h1>
<p class="subtitle">Generated {TODAY_STR} — Empower API source of truth</p>
<p class="subtitle">Weekly: {PERIODS['weekly'][0]} → {PERIODS['weekly'][1]} (7 days) · MTD: {PERIODS['mtd'][0]} → {PERIODS['mtd'][1]}</p>

{period_html(weekly, "weekly")}

{mtd_banner(mtd)}

{period_html(mtd, "mtd")}

<footer>
  Source: Empower API ({API_BASE}) — /api/dashboard/summary, /api/spending, /api/spending/merchants, /api/transactions<br>
  No cron-owned SQL. Period labels verified against PERIOD_META.
</footer>
</body>
</html>
"""

html = build_report_html(PERIODS, weekly, mtd, meta_json, API_BASE, TODAY_STR)

with open(REPORT_FILE, "w", encoding="utf-8") as fh:
    fh.write(html)

print(json.dumps(period_meta))
PYEOF

if [[ ! -f "$REPORT_FILE" ]]; then
  die "Report file missing: $REPORT_FILE"
fi
if [[ ! -s "$REPORT_FILE" ]]; then
  die "Report file empty: $REPORT_FILE"
fi

WEEKLY_START="$(date -d "$REPORT_DATE -6 days" +%Y-%m-%d)"
MTD_START="$(date -d "$REPORT_DATE" +%Y-%m-01)"

if ! grep -q 'PERIOD_META' "$REPORT_FILE"; then
  die "Report missing PERIOD_META marker"
fi

for pair in \
  "weekly_start:${WEEKLY_START}" \
  "weekly_end:${REPORT_DATE}" \
  "mtd_start:${MTD_START}" \
  "mtd_end:${REPORT_DATE}"; do
  key="${pair%%:*}"
  val="${pair#*:}"
  if ! grep -q "\"${key}\":\"${val}\"" "$REPORT_FILE"; then
    die "Period mismatch: expected ${key}=${val} in PERIOD_META"
  fi
done

WS="$WEEKLY_START"
WE="$REPORT_DATE"
MS="$MTD_START"
ME="$REPORT_DATE"

WEEKLY_SUMMARY=$(curl -sf "${EMPOWER_API}/api/dashboard/summary?start_date=${WS}&end_date=${WE}")
MTD_SUMMARY=$(curl -sf "${EMPOWER_API}/api/dashboard/summary?start_date=${MS}&end_date=${ME}")

W_INCOME=$(echo "$WEEKLY_SUMMARY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total_income',0))")
W_EXP=$(echo "$WEEKLY_SUMMARY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total_expenses',0))")
W_NET=$(echo "$WEEKLY_SUMMARY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('net',0))")
M_INCOME=$(echo "$MTD_SUMMARY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total_income',0))")
M_EXP=$(echo "$MTD_SUMMARY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total_expenses',0))")
M_NET=$(echo "$MTD_SUMMARY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('net',0))")

log "Report verified: $REPORT_FILE ($(wc -c < "$REPORT_FILE") bytes)"

echo "WEEKLY_FINANCE_REPORT_OK"
echo "REPORT_PATH=${REPORT_FILE}"
echo "PERIOD weekly=${WS}..${WE} mtd=${MS}..${ME}"
echo "WEEKLY income=${W_INCOME} expenses=${W_EXP} net=${W_NET}"
echo "MTD income=${M_INCOME} expenses=${M_EXP} net=${M_NET}"
