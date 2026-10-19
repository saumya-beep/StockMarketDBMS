
from flask import Flask, render_template_string, request, redirect, url_for, flash
from db import get_connection
from decimal import Decimal

app = Flask(__name__)
app.secret_key = "change-this-demo-secret"

ACCOUNT_ID = 1
PORTFOLIO_ID = 1

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stock Market Management</title>
<style>
*{box-sizing:border-box}
body{margin:0;font-family:Arial,sans-serif;background:#f3f6fb;color:#172033}
header{background:#101b35;color:white;padding:25px 5%}
header h1{margin:0 0 8px}
main{max-width:1150px;margin:28px auto;padding:0 20px}
.balance,.panel,.card{background:white;border-radius:14px;padding:22px;box-shadow:0 3px 12px #1720330d}
.balance{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:15px;margin-bottom:22px}
.balance strong{font-size:30px;color:#16794b}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px;margin-bottom:24px}
.symbol{color:#2563eb;font-weight:bold}
.price{font-size:26px;font-weight:bold;margin:14px 0}
.company{color:#64748b;min-height:36px}
form{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
input,select,button{padding:10px;border:1px solid #cbd5e1;border-radius:7px;font-size:14px}
input,select{min-width:0;flex:1;width:100%}
button{border:0;color:white;background:#2563eb;cursor:pointer;font-weight:bold}
button.sell{background:#d94848}
button:hover{opacity:.88}
.panel{margin-bottom:22px;overflow-x:auto}
table{border-collapse:collapse;width:100%;margin-top:12px}
th,td{text-align:left;padding:12px;border-bottom:1px solid #e2e8f0}
th{background:#f8fafc}
.message{padding:12px;border-radius:8px;margin-bottom:12px;background:#dcfce7;color:#166534}
.error{background:#fee2e2;color:#991b1b}
.note{color:#64748b;font-size:13px;margin:20px 0}
</style>
</head>
<body>
<header>
<h1>Stock Market Management</h1>
<p>Oracle-powered dashboard · Simulated trading</p>
</header>
<main>
{% with messages = get_flashed_messages(with_categories=true) %}
{% for category,message in messages %}
<div class="message {{ 'error' if category == 'error' else '' }}">{{ message }}</div>
{% endfor %}
{% endwith %}

<section class="balance">
<div><div>Available account balance</div><strong>₹{{ "%.2f"|format(balance) }}</strong></div>
<div>Demo Account #{{ account_id }}</div>
</section>

<h2>Market Stocks</h2>
<section class="grid">
{% for s in stocks %}
<article class="card">
<div class="symbol">{{ s[1] }}</div>
<div class="price">₹{{ "%.2f"|format(s[2]) }}</div>
<div class="company">{{ s[3] }}</div>
<form method="post" action="{{ url_for('trade') }}">
<input type="hidden" name="stock_id" value="{{ s[0] }}">
<input type="number" name="quantity" min="1" step="1" value="1" required aria-label="Quantity">
<button name="trade_type" value="BUY">Buy</button>
<button class="sell" name="trade_type" value="SELL">Sell</button>
</form>
</article>
{% endfor %}
</section>

<section class="panel">
<h2>Your Portfolio</h2>
<table><thead><tr><th>Stock</th><th>Quantity</th><th>Average buy price</th><th>Current value</th></tr></thead>
<tbody>
{% for h in holdings %}
<tr><td>{{ h[0] }}</td><td>{{ h[1] }}</td><td>₹{{ "%.2f"|format(h[2]) }}</td><td>₹{{ "%.2f"|format(h[3]) }}</td></tr>
{% else %}
<tr><td colspan="4">No holdings yet. Buy a stock to start your portfolio.</td></tr>
{% endfor %}
</tbody></table>
</section>

<section class="panel">
<h2>Recent Transactions</h2>
<table><thead><tr><th>Date</th><th>Type</th><th>Amount</th><th>Reference</th></tr></thead>
<tbody>
{% for t in transactions %}
<tr><td>{{ t[0] }}</td><td>{{ t[1] }}</td><td>₹{{ "%.2f"|format(t[2]) }}</td><td>{{ t[3] }}</td></tr>
{% else %}
<tr><td colspan="4">No transactions yet.</td></tr>
{% endfor %}
</tbody></table>
</section>
<p class="note">Educational simulation only. Prices are sample data, not live prices. No real money or external market orders are involved.</p>
</main>
</body>
</html>
"""


def load_dashboard():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT BALANCE FROM TRADING_ACCOUNT WHERE ACCOUNT_ID = :id",
                id=ACCOUNT_ID,
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError("Demo trading account 1 was not found.")
            balance = float(row[0])

            cursor.execute("""
                SELECT S.STOCK_ID, S.SYMBOL, S.CURRENT_PRICE, C.COMPANY_NAME
                FROM STOCK S
                JOIN COMPANY C ON C.COMPANY_ID = S.COMPANY_ID
                ORDER BY S.STOCK_ID
            """)
            stocks = cursor.fetchall()

            cursor.execute("""
                SELECT S.SYMBOL, H.QUANTITY, H.AVG_BUY_PRICE,
                       H.QUANTITY * S.CURRENT_PRICE AS CURRENT_VALUE
                FROM HOLDING H
                JOIN STOCK S ON S.STOCK_ID = H.STOCK_ID
                WHERE H.PORTFOLIO_ID = :portfolio_id
                ORDER BY S.SYMBOL
            """, portfolio_id=PORTFOLIO_ID)
            holdings = [
                (r[0], int(r[1]), float(r[2]), float(r[3]))
                for r in cursor.fetchall()
            ]

            cursor.execute("""
                SELECT TRANSACTION_DATE, TYPE, AMOUNT, REFERENCE
                FROM STOCK_TRANSACTION
                WHERE ACCOUNT_ID = :id
                ORDER BY TRANSACTION_ID DESC
            """, id=ACCOUNT_ID)
            transactions = [
                (r[0].strftime("%Y-%m-%d %H:%M") if r[0] else "",
                 r[1], float(r[2]), r[3] or "")
                for r in cursor.fetchall()
            ]

    return balance, stocks, holdings, transactions


@app.route("/")
def dashboard():
    try:
        balance, stocks, holdings, transactions = load_dashboard()
        return render_template_string(
            HTML, balance=balance, stocks=stocks, holdings=holdings,
            transactions=transactions, account_id=ACCOUNT_ID
        )
    except Exception:
        app.logger.exception("Dashboard database error")
        return "Could not load dashboard. Check the VS Code terminal for the database error.", 500


@app.route("/trade", methods=["POST"])
def trade():
    trade_type = request.form.get("trade_type", "").upper()
    try:
        stock_id = int(request.form["stock_id"])
        quantity = int(request.form["quantity"])
        if trade_type not in ("BUY", "SELL") or quantity <= 0:
            raise ValueError("Choose Buy or Sell and enter a positive whole-number quantity.")

        with get_connection() as connection:
            with connection.cursor() as cursor:
                # Lock the account row so concurrent trades cannot spend the same balance.
                cursor.execute("""
                    SELECT BALANCE FROM TRADING_ACCOUNT
                    WHERE ACCOUNT_ID = :id FOR UPDATE
                """, id=ACCOUNT_ID)
                account = cursor.fetchone()
                if account is None:
                    raise ValueError("Trading account not found.")
                balance = Decimal(str(account[0]))

                cursor.execute("""
                    SELECT CURRENT_PRICE, SYMBOL FROM STOCK
                    WHERE STOCK_ID = :id
                """, id=stock_id)
                stock = cursor.fetchone()
                if stock is None:
                    raise ValueError("Stock not found.")
                price = Decimal(str(stock[0]))
                symbol = stock[1]
                total = price * quantity

                cursor.execute("""
                    SELECT NVL(MAX(ORDER_ID), 0) + 1 FROM STOCK_ORDER
                """)
                order_id = int(cursor.fetchone()[0])
                cursor.execute("SELECT NVL(MAX(TRADE_ID), 0) + 1 FROM TRADE")
                trade_id = int(cursor.fetchone()[0])
                cursor.execute("""
                    SELECT NVL(MAX(TRANSACTION_ID), 0) + 1
                    FROM STOCK_TRANSACTION
                """)
                transaction_id = int(cursor.fetchone()[0])

                if trade_type == "BUY":
                    if balance < total:
                        raise ValueError("Insufficient balance for this purchase.")

                    cursor.execute("""
                        UPDATE TRADING_ACCOUNT
                        SET BALANCE = BALANCE - :amount
                        WHERE ACCOUNT_ID = :id
                    """, amount=float(total), id=ACCOUNT_ID)

                    cursor.execute("""
                        SELECT QUANTITY, AVG_BUY_PRICE, HOLDING_ID
                        FROM HOLDING
                        WHERE PORTFOLIO_ID = :pid AND STOCK_ID = :sid
                        FOR UPDATE
                    """, pid=PORTFOLIO_ID, sid=stock_id)
                    holding = cursor.fetchone()

                    if holding:
                        old_qty, old_avg, holding_id = holding
                        new_qty = int(old_qty) + quantity
                        new_avg = (
                            Decimal(str(old_avg)) * int(old_qty) + total
                        ) / new_qty
                        cursor.execute("""
                            UPDATE HOLDING
                            SET QUANTITY = :qty, AVG_BUY_PRICE = :avg,
                                CURRENT_VALUE = :value
                            WHERE HOLDING_ID = :hid
                        """, qty=new_qty, avg=float(new_avg),
                             value=float(new_qty * price), hid=holding_id)
                    else:
                        cursor.execute("SELECT NVL(MAX(HOLDING_ID), 0) + 1 FROM HOLDING")
                        holding_id = int(cursor.fetchone()[0])
                        cursor.execute("""
                            INSERT INTO HOLDING
                            (HOLDING_ID, QUANTITY, AVG_BUY_PRICE, CURRENT_VALUE,
                             PORTFOLIO_ID, STOCK_ID)
                            VALUES (:hid, :qty, :avg, :value, :pid, :sid)
                        """, hid=holding_id, qty=quantity, avg=float(price),
                             value=float(total), pid=PORTFOLIO_ID, sid=stock_id)

                else:
                    cursor.execute("""
                        SELECT QUANTITY, HOLDING_ID FROM HOLDING
                        WHERE PORTFOLIO_ID = :pid AND STOCK_ID = :sid
                        FOR UPDATE
                    """, pid=PORTFOLIO_ID, sid=stock_id)
                    holding = cursor.fetchone()
                    if not holding or int(holding[0]) < quantity:
                        raise ValueError("You do not own enough shares to sell.")

                    remaining = int(holding[0]) - quantity
                    cursor.execute("""
                        UPDATE TRADING_ACCOUNT
                        SET BALANCE = BALANCE + :amount
                        WHERE ACCOUNT_ID = :id
                    """, amount=float(total), id=ACCOUNT_ID)

                    if remaining == 0:
                        cursor.execute(
                            "DELETE FROM HOLDING WHERE HOLDING_ID = :id",
                            id=holding[1],
                        )
                    else:
                        cursor.execute("""
                            UPDATE HOLDING
                            SET QUANTITY = :qty, CURRENT_VALUE = :value
                            WHERE HOLDING_ID = :hid
                        """, qty=remaining, value=float(remaining * price),
                             hid=holding[1])

                cursor.execute("""
                    INSERT INTO STOCK_ORDER
                    (ORDER_ID, ORDER_TYPE, ORDER_DATE, PRICE, QUANTITY,
                     STATUS, ACCOUNT_ID, STOCK_ID)
                    VALUES (:oid, :typ, SYSDATE, :price, :qty,
                            'COMPLETED', :aid, :sid)
                """, oid=order_id, typ=trade_type, price=float(price),
                     qty=quantity, aid=ACCOUNT_ID, sid=stock_id)

                cursor.execute("""
                    INSERT INTO TRADE
                    (TRADE_ID, TRADE_DATE, QUANTITY, EXECUTION_PRICE,
                     TRADE_TYPE, ORDER_ID, STOCK_ID)
                    VALUES (:tid, SYSDATE, :qty, :price, :typ, :oid, :sid)
                """, tid=trade_id, qty=quantity, price=float(price),
                     typ=trade_type, oid=order_id, sid=stock_id)

                cursor.execute("""
                    INSERT INTO STOCK_TRANSACTION
                    (TRANSACTION_ID, TRANSACTION_DATE, AMOUNT, TYPE,
                     REFERENCE, ACCOUNT_ID)
                    VALUES (:tid, SYSDATE, :amount, :typ, :ref, :aid)
                """, tid=transaction_id, amount=float(total),
                     typ=trade_type, ref=f"{trade_type} {quantity} {symbol}",
                     aid=ACCOUNT_ID)

            connection.commit()

        flash(f"{trade_type} successful: {quantity} share(s) of {symbol} for ₹{total:.2f}.")
    except (ValueError, KeyError, TypeError) as error:
        flash(str(error), "error")
    except Exception:
        app.logger.exception("Trade failed")
        flash("Trade failed. No changes were saved; check the terminal for details.", "error")

    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True)
