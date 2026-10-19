import os
from decimal import Decimal, InvalidOperation
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from db import get_connection

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "local-demo-secret-change-me")

ACCOUNT_ID = 1
PORTFOLIO_ID = 1


def fetch_all(cursor):
    columns = [column[0].lower() for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def fetch_one(cursor):
    columns = [column[0].lower() for column in cursor.description]
    row = cursor.fetchone()
    return dict(zip(columns, row)) if row else None


def get_account(cursor):
    cursor.execute("""
        SELECT A.ACCOUNT_ID, A.ACCOUNT_TYPE, A.OPEN_DATE, A.BALANCE,
               A.INVESTOR_ID, I.NAME, I.EMAIL, I.PHONE, I.ADDRESS,
               B.EMAIL AS BROKER_EMAIL
        FROM TRADING_ACCOUNT A
        JOIN INVESTOR I ON I.INVESTOR_ID = A.INVESTOR_ID
        LEFT JOIN BROKER B ON B.BROKER_ID = A.BROKER_ID
        WHERE A.ACCOUNT_ID = :aid
    """, aid=ACCOUNT_ID)
    return fetch_one(cursor)


def get_stocks(cursor):
    cursor.execute("""
        SELECT S.STOCK_ID, S.SYMBOL, S.CURRENT_PRICE AS PRICE,
               C.COMPANY_NAME, MS.SECTOR_NAME
        FROM STOCK S
        JOIN COMPANY C ON C.COMPANY_ID = S.COMPANY_ID
        LEFT JOIN MARKET_SECTOR MS ON MS.SECTOR_ID = C.SECTOR_ID
        ORDER BY S.SYMBOL
    """)
    return fetch_all(cursor)


def get_holdings(cursor):
    cursor.execute("""
        SELECT H.HOLDING_ID, H.STOCK_ID, S.SYMBOL,
               C.COMPANY_NAME, H.QUANTITY, H.AVG_BUY_PRICE AS AVG_PRICE,
               S.CURRENT_PRICE AS PRICE,
               H.QUANTITY * S.CURRENT_PRICE AS CURRENT_VALUE,
               H.QUANTITY * H.AVG_BUY_PRICE AS INVESTED_VALUE,
               H.QUANTITY * (S.CURRENT_PRICE - H.AVG_BUY_PRICE) AS PROFIT_LOSS
        FROM HOLDING H
        JOIN STOCK S ON S.STOCK_ID = H.STOCK_ID
        JOIN COMPANY C ON C.COMPANY_ID = S.COMPANY_ID
        WHERE H.PORTFOLIO_ID = :pid
        ORDER BY S.SYMBOL
    """, pid=PORTFOLIO_ID)
    return fetch_all(cursor)


def get_transactions(cursor):
    cursor.execute("""
        SELECT TRANSACTION_ID, TRANSACTION_DATE, TYPE, AMOUNT, REFERENCE
        FROM STOCK_TRANSACTION
        WHERE ACCOUNT_ID = :aid
        ORDER BY TRANSACTION_ID DESC
    """, aid=ACCOUNT_ID)
    return fetch_all(cursor)


def portfolio_totals(holdings):
    invested = sum(
        (Decimal(str(h["invested_value"] or 0)) for h in holdings),
        Decimal("0")
    )
    value = sum(
        (Decimal(str(h["current_value"] or 0)) for h in holdings),
        Decimal("0")
    )
    return invested, value, value - invested


@app.route("/")
def dashboard():
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                account = get_account(cursor)

                if not account:
                    return "Demo trading account not found in Oracle.", 500

                stocks = get_stocks(cursor)
                holdings = get_holdings(cursor)
                transactions = get_transactions(cursor)
                invested, value, pnl = portfolio_totals(holdings)

                # Calculate stock price changes using the latest
                # and previous available daily closing prices.
                cursor.execute("""
                    SELECT
                        s.stock_id,
                        s.symbol,
                        c.company_name,
                        s.current_price,
                        (
                            SELECT h.close_price
                            FROM stock_price_history h
                            WHERE h.stock_id = s.stock_id
                              AND h.interval_type = '1d'
                              AND h.recorded_at = (
                                  SELECT MAX(h2.recorded_at)
                                  FROM stock_price_history h2
                                  WHERE h2.stock_id = s.stock_id
                                    AND h2.interval_type = '1d'
                                    AND h2.recorded_at < (
                                        SELECT MAX(h3.recorded_at)
                                        FROM stock_price_history h3
                                        WHERE h3.stock_id = s.stock_id
                                          AND h3.interval_type = '1d'
                                    )
                              )
                        ) AS previous_price
                    FROM stock s
                    JOIN company c
                      ON c.company_id = s.company_id
                """)

                market_changes = fetch_all(cursor)

                # Calculate percentage change.
                for item in market_changes:
                    previous = item["previous_price"]
                    current = item["current_price"]

                    if previous is not None and previous != 0:
                        item["change_percent"] = round(
                            (float(current) - float(previous))
                            / float(previous) * 100,
                            2
                        )
                    else:
                        item["change_percent"] = None

                market_changes = [
                    item for item in market_changes
                    if item["change_percent"] is not None
                ]

                gainers = sorted(
                    market_changes,
                    key=lambda item: item["change_percent"],
                    reverse=True
                )[:5]

                losers = sorted(
                    market_changes,
                    key=lambda item: item["change_percent"]
                )[:5]

                # Market summary.
                total_market_stocks = len(market_changes)

                advancing_count = sum(
                    1 for item in market_changes
                    if item["change_percent"] > 0
                )

                declining_count = sum(
                    1 for item in market_changes
                    if item["change_percent"] < 0
                )

                unchanged_count = (
                    total_market_stocks
                    - advancing_count
                    - declining_count
                )

                average_change = (
                    sum(
                        item["change_percent"]
                        for item in market_changes
                    ) / total_market_stocks
                    if total_market_stocks else 0
                )

                return render_template(
                    "dashboard.html",
                    balance=account["balance"],
                    stocks=stocks,
                    holdings=holdings[:5],
                    transactions=transactions[:5],
                    total_invested=invested,
                    portfolio_value=value,
                    pnl=pnl,
                    gainers=gainers,
                    losers=losers,
                    total_market_stocks=total_market_stocks,
                    advancing_count=advancing_count,
                    declining_count=declining_count,
                    unchanged_count=unchanged_count,
                    average_change=average_change
                )

    except Exception:
        app.logger.exception("Dashboard database error")
        return "Could not load dashboard. Check the VS Code terminal.", 500



@app.route("/stocks")
def stocks():
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                return render_template("stocks.html", stocks=get_stocks(cursor))
    except Exception:
        app.logger.exception("Stocks page error")
        return "Could not load stocks. Check the VS Code terminal.", 500


@app.route("/portfolio")
def portfolio():
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                holdings = get_holdings(cursor)
                invested, value, pnl = portfolio_totals(holdings)
                return render_template(
                    "portfolio.html", holdings=holdings,
                    total_invested=invested, portfolio_value=value, pnl=pnl
                )
    except Exception:
        app.logger.exception("Portfolio page error")
        return "Could not load portfolio. Check the VS Code terminal.", 500


@app.route("/orders")
def orders():
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT O.ORDER_ID, O.ORDER_DATE, O.ORDER_TYPE,
                           O.QUANTITY, O.PRICE, O.STATUS, S.SYMBOL
                    FROM STOCK_ORDER O
                    JOIN STOCK S ON S.STOCK_ID = O.STOCK_ID
                    WHERE O.ACCOUNT_ID = :aid
                    ORDER BY O.ORDER_ID DESC
                """, aid=ACCOUNT_ID)
                order_rows = fetch_all(cursor)

                cursor.execute("""
                    SELECT T.TRADE_ID, T.TRADE_DATE, T.QUANTITY,
                           T.EXECUTION_PRICE, T.TRADE_TYPE, S.SYMBOL
                    FROM TRADE T
                    JOIN STOCK S ON S.STOCK_ID = T.STOCK_ID
                    JOIN STOCK_ORDER O ON O.ORDER_ID = T.ORDER_ID
                    WHERE O.ACCOUNT_ID = :aid
                    ORDER BY T.TRADE_ID DESC
                """, aid=ACCOUNT_ID)
                trade_rows = fetch_all(cursor)

                return render_template(
                    "orders.html", orders=order_rows, trades=trade_rows
                )
    except Exception:
        app.logger.exception("Orders page error")
        return "Could not load orders. Check the VS Code terminal.", 500


@app.route("/transactions")
def transactions():
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                return render_template(
                    "transactions.html",
                    transactions=get_transactions(cursor)
                )
    except Exception:
        app.logger.exception("Transactions page error")
        return "Could not load transactions. Check the VS Code terminal.", 500


@app.route("/watchlists")
def watchlists():
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT WATCHLIST_ID, WATCHLIST_NAME
                    FROM WATCHLIST
                    WHERE ACCOUNT_ID = :aid
                    ORDER BY WATCHLIST_ID
                """, aid=ACCOUNT_ID)
                lists = fetch_all(cursor)

                for item in lists:
                    cursor.execute("""
                        SELECT S.STOCK_ID, S.SYMBOL, S.CURRENT_PRICE AS PRICE,
                               C.COMPANY_NAME, MS.SECTOR_NAME
                        FROM WATCHLIST_STOCK WS
                        JOIN STOCK S ON S.STOCK_ID = WS.STOCK_ID
                        JOIN COMPANY C ON C.COMPANY_ID = S.COMPANY_ID
                        LEFT JOIN MARKET_SECTOR MS ON MS.SECTOR_ID = C.SECTOR_ID
                        WHERE WS.WATCHLIST_ID = :wid
                        ORDER BY S.SYMBOL
                    """, wid=item["watchlist_id"])
                    item["stocks"] = fetch_all(cursor)

                return render_template("watchlists.html", watchlists=lists)
    except Exception:
        app.logger.exception("Watchlists page error")
        return "Could not load watchlists. Check the VS Code terminal.", 500

    
@app.route("/watchlist/add/<int:stock_id>", methods=["POST"])
def add_to_watchlist(stock_id):
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                # Find the user's existing watchlist.
                cursor.execute("""
                    SELECT WATCHLIST_ID
                    FROM WATCHLIST
                    WHERE ACCOUNT_ID = :aid
                    ORDER BY WATCHLIST_ID
                """, aid=ACCOUNT_ID)

                result = cursor.fetchone()

                if not result:
                    flash("No watchlist found for this account.", "error")
                    return redirect(url_for("stocks"))

                watchlist_id = result[0]

                # Check that the stock exists.
                cursor.execute("""
                    SELECT STOCK_ID
                    FROM STOCK
                    WHERE STOCK_ID = :sid
                """, sid=stock_id)

                if not cursor.fetchone():
                    flash("Stock not found.", "error")
                    return redirect(url_for("stocks"))

                # Prevent duplicate entries.
                cursor.execute("""
                    SELECT 1
                    FROM WATCHLIST_STOCK
                    WHERE WATCHLIST_ID = :wid
                      AND STOCK_ID = :sid
                """, wid=watchlist_id, sid=stock_id)

                if cursor.fetchone():
                    flash("This stock is already in your watchlist.", "info")
                else:
                    cursor.execute("""
                        INSERT INTO WATCHLIST_STOCK
                            (WATCHLIST_ID, STOCK_ID)
                        VALUES (:wid, :sid)
                    """, wid=watchlist_id, sid=stock_id)

                    connection.commit()
                    flash("Stock added to your watchlist.", "success")

        return redirect(url_for("stocks"))

    except Exception:
        app.logger.exception("Add to watchlist error")
        flash("Could not add stock to watchlist.", "error")
        return redirect(url_for("stocks"))
@app.route("/watchlist/remove", methods=["POST"])
def remove_watchlist_stock():
    try:
        watchlist_id = request.form.get("watchlist_id", type=int)
        stock_id = request.form.get("stock_id", type=int)

        if not watchlist_id or not stock_id:
            flash("Invalid watchlist or stock.", "error")
            return redirect(url_for("watchlists"))

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT WATCHLIST_ID
                    FROM WATCHLIST
                    WHERE WATCHLIST_ID = :wid
                      AND ACCOUNT_ID = :aid
                """, wid=watchlist_id, aid=ACCOUNT_ID)

                if not cursor.fetchone():
                    flash("Watchlist not found for this account.", "error")
                    return redirect(url_for("watchlists"))

                cursor.execute("""
                    DELETE FROM WATCHLIST_STOCK
                    WHERE WATCHLIST_ID = :wid
                      AND STOCK_ID = :sid
                """, wid=watchlist_id, sid=stock_id)

                if cursor.rowcount == 0:
                    flash("Stock was not found in this watchlist.", "info")
                else:
                    connection.commit()
                    flash("Stock removed from your watchlist.", "success")

        return redirect(url_for("watchlists"))

    except Exception:
        app.logger.exception("Remove from watchlist error")
        flash("Could not remove stock from watchlist.", "error")
        return redirect(url_for("watchlists"))



@app.route("/companies")
def companies():
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT C.COMPANY_ID, C.COMPANY_NAME, C.FOUNDED_YEAR,
                           MS.SECTOR_NAME, S.SYMBOL, S.CURRENT_PRICE AS PRICE
                    FROM COMPANY C
                    LEFT JOIN MARKET_SECTOR MS ON MS.SECTOR_ID = C.SECTOR_ID
                    LEFT JOIN STOCK S ON S.COMPANY_ID = C.COMPANY_ID
                    ORDER BY C.COMPANY_NAME
                """)
                return render_template(
                    "companies.html", companies=fetch_all(cursor)
                )
    except Exception:
        app.logger.exception("Companies page error")
        return "Could not load companies. Check the VS Code terminal.", 500
    
@app.route("/companies/update", methods=["POST"])
def update_company():
    try:
        company_id = request.form.get("company_id", type=int)
        year_text = request.form.get("founded_year", "").strip()

        if not company_id:
            flash("Invalid company ID.", "error")
            return redirect(url_for("companies"))

        founded_year = None

        if year_text:
            founded_year = int(year_text)

            if founded_year < 1800 or founded_year > 2026:
                flash("Enter a valid founded year.", "error")
                return redirect(url_for("companies"))

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE COMPANY
                    SET FOUNDED_YEAR = :year
                    WHERE COMPANY_ID = :cid
                """, year=founded_year, cid=company_id)

                if cursor.rowcount == 0:
                    flash("Company not found.", "error")
                else:
                    connection.commit()
                    flash("Company founded year updated successfully.", "success")

        return redirect(url_for("companies"))

    except Exception:
        app.logger.exception("Update company error")
        flash("Could not update company. Check the VS Code terminal.", "error")
        return redirect(url_for("companies"))



@app.route("/dividends")
def dividends():
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT D.DIVIDEND_ID, D.DIVIDEND_PER_SHARE,
                           D.RECORD_DATE, D.PAYMENT_DATE, S.SYMBOL,
                           C.COMPANY_NAME
                    FROM DIVIDEND D
                    JOIN STOCK S ON S.STOCK_ID = D.STOCK_ID
                    JOIN COMPANY C ON C.COMPANY_ID = S.COMPANY_ID
                    ORDER BY D.PAYMENT_DATE DESC NULLS LAST
                """)
                return render_template(
                    "dividends.html", dividends=fetch_all(cursor)
                )
    except Exception:
        app.logger.exception("Dividends page error")
        return "Could not load dividends. Check the VS Code terminal.", 500


@app.route("/account")
def account():
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                details = get_account(cursor)
                if not details:
                    return "Demo trading account not found.", 404
                investor = {
                    "investor_id": details["investor_id"],
                    "name": details["name"],
                    "email": details["email"],
                    "phone": details["phone"],
                    "address": details["address"],
                }
                return render_template(
                    "account.html", investor=investor, account=details
                )
    except Exception:
        app.logger.exception("Account page error")
        return "Could not load account. Check the VS Code terminal.", 500


@app.route("/trade", methods=["POST"])
def trade():
    # Accept both names so the old and new templates can submit trades.
    trade_type = (
        request.form.get("order_type")
        or request.form.get("trade_type", "")
    ).upper()

    try:
        stock_id = int(request.form["stock_id"])
        quantity = int(request.form["quantity"])

        if trade_type not in ("BUY", "SELL") or quantity <= 0:
            raise ValueError("Choose Buy or Sell and enter a positive whole-number quantity.")

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT BALANCE FROM TRADING_ACCOUNT
                    WHERE ACCOUNT_ID = :aid FOR UPDATE
                """, aid=ACCOUNT_ID)
                account_row = cursor.fetchone()
                if not account_row:
                    raise ValueError("Trading account not found.")

                balance = Decimal(str(account_row[0]))

                cursor.execute("""
                    SELECT CURRENT_PRICE, SYMBOL FROM STOCK
                    WHERE STOCK_ID = :sid
                """, sid=stock_id)
                stock = cursor.fetchone()
                if not stock:
                    raise ValueError("Stock not found.")

                price = Decimal(str(stock[0]))
                symbol = stock[1]
                total = price * quantity

                cursor.execute(
                    "SELECT NVL(MAX(ORDER_ID),0)+1 FROM STOCK_ORDER"
                )
                order_id = int(cursor.fetchone()[0])
                cursor.execute("SELECT NVL(MAX(TRADE_ID),0)+1 FROM TRADE")
                trade_id = int(cursor.fetchone()[0])
                cursor.execute(
                    "SELECT NVL(MAX(TRANSACTION_ID),0)+1 FROM STOCK_TRANSACTION"
                )
                transaction_id = int(cursor.fetchone()[0])

                if trade_type == "BUY":
                    if balance < total:
                        raise ValueError("Insufficient balance for this purchase.")

                    cursor.execute("""
                        UPDATE TRADING_ACCOUNT SET BALANCE = BALANCE - :amount
                        WHERE ACCOUNT_ID = :aid
                    """, amount=float(total), aid=ACCOUNT_ID)

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
                            SET QUANTITY=:qty, AVG_BUY_PRICE=:avg,
                                CURRENT_VALUE=:value
                            WHERE HOLDING_ID=:hid
                        """, qty=new_qty, avg=float(new_avg),
                             value=float(new_qty * price), hid=holding_id)
                    else:
                        cursor.execute(
                            "SELECT NVL(MAX(HOLDING_ID),0)+1 FROM HOLDING"
                        )
                        holding_id = int(cursor.fetchone()[0])
                        cursor.execute("""
                            INSERT INTO HOLDING
                            (HOLDING_ID, QUANTITY, AVG_BUY_PRICE,
                             CURRENT_VALUE, PORTFOLIO_ID, STOCK_ID)
                            VALUES (:hid,:qty,:avg,:value,:pid,:sid)
                        """, hid=holding_id, qty=quantity, avg=float(price),
                             value=float(total), pid=PORTFOLIO_ID, sid=stock_id)
                else:
                    cursor.execute("""
                        SELECT QUANTITY, HOLDING_ID FROM HOLDING
                        WHERE PORTFOLIO_ID=:pid AND STOCK_ID=:sid
                        FOR UPDATE
                    """, pid=PORTFOLIO_ID, sid=stock_id)
                    holding = cursor.fetchone()

                    if not holding or int(holding[0]) < quantity:
                        raise ValueError("You do not own enough shares to sell.")

                    remaining = int(holding[0]) - quantity
                    cursor.execute("""
                        UPDATE TRADING_ACCOUNT SET BALANCE = BALANCE + :amount
                        WHERE ACCOUNT_ID = :aid
                    """, amount=float(total), aid=ACCOUNT_ID)

                    if remaining == 0:
                        cursor.execute(
                            "DELETE FROM HOLDING WHERE HOLDING_ID=:hid",
                            hid=holding[1]
                        )
                    else:
                        cursor.execute("""
                            UPDATE HOLDING SET QUANTITY=:qty,
                                CURRENT_VALUE=:value WHERE HOLDING_ID=:hid
                        """, qty=remaining, value=float(remaining * price),
                             hid=holding[1])

                cursor.execute("""
                    INSERT INTO STOCK_ORDER
                    (ORDER_ID, ORDER_TYPE, ORDER_DATE, PRICE, QUANTITY,
                     STATUS, ACCOUNT_ID, STOCK_ID)
                    VALUES (:oid,:typ,SYSDATE,:price,:qty,
                            'COMPLETED',:aid,:sid)
                """, oid=order_id, typ=trade_type, price=float(price),
                     qty=quantity, aid=ACCOUNT_ID, sid=stock_id)

                cursor.execute("""
                    INSERT INTO TRADE
                    (TRADE_ID, TRADE_DATE, QUANTITY, EXECUTION_PRICE,
                     TRADE_TYPE, ORDER_ID, STOCK_ID)
                    VALUES (:tid,SYSDATE,:qty,:price,:typ,:oid,:sid)
                """, tid=trade_id, qty=quantity, price=float(price),
                     typ=trade_type, oid=order_id, sid=stock_id)

                cursor.execute("""
                    INSERT INTO STOCK_TRANSACTION
                    (TRANSACTION_ID, TRANSACTION_DATE, AMOUNT, TYPE,
                     REFERENCE, ACCOUNT_ID)
                    VALUES (:tid,SYSDATE,:amount,:typ,:ref,:aid)
                """, tid=transaction_id, amount=float(total), typ=trade_type,
                     ref=f"{trade_type} {quantity} {symbol}", aid=ACCOUNT_ID)

            connection.commit()

        flash(f"{trade_type} successful: {quantity} share(s) of {symbol} for ₹{total:.2f}.")
    except (ValueError, KeyError, TypeError, InvalidOperation) as error:
        flash(str(error), "error")
    except Exception:
        app.logger.exception("Trade failed")
        flash("Trade failed. No changes were saved; check the terminal for details.", "error")

    return redirect(url_for("stocks") if request.referrer and "/stocks" in request.referrer
                    else url_for("dashboard"))
@app.route("/stock/<int:stock_id>")
def stock_detail(stock_id):
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT S.STOCK_ID, S.SYMBOL, S.CURRENT_PRICE,
                           C.COMPANY_NAME
                    FROM STOCK S
                    JOIN COMPANY C ON C.COMPANY_ID = S.COMPANY_ID
                    WHERE S.STOCK_ID = :sid
                """, sid=stock_id)

                stock = fetch_one(cursor)

                if not stock:
                    return "Stock not found.", 404

                return render_template("stock_detail.html", stock=stock)

    except Exception:
        app.logger.exception("Stock detail page error")
        return "Could not load stock details. Check the terminal.", 500


@app.route("/api/stocks/<int:stock_id>/history")
def stock_history(stock_id):
    period = request.args.get("period", "1M").upper()

    # Daily history is available for these periods.
    days_by_period = {
        "1W": 7,
        "1M": 30,
        "1Y": 365
    }

    if period == "1D":
        return jsonify({
            "data": [],
            "message": (
                "Intraday historical data is not available yet. "
                "Daily closing prices cannot provide an intraday chart."
            )
        })

    if period not in days_by_period:
        return jsonify({"error": "Invalid chart period"}), 400

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT S.STOCK_ID
                    FROM STOCK S
                    WHERE S.STOCK_ID = :sid
                """, sid=stock_id)

                if not cursor.fetchone():
                    return jsonify({"error": "Stock not found"}), 404

                cursor.execute("""
                    SELECT RECORDED_AT,
                           NVL(CLOSE_PRICE, PRICE) AS CLOSE_PRICE
                    FROM STOCK_PRICE_HISTORY
                    WHERE STOCK_ID = :sid
                      AND INTERVAL_TYPE = '1d'
                      AND RECORDED_AT >= TRUNC(SYSDATE) - :days
                    ORDER BY RECORDED_AT
                """, sid=stock_id, days=days_by_period[period])

                data = [
                    {
                        "time": row[0].strftime("%Y-%m-%d"),
                        "value": float(row[1])
                    }
                    for row in cursor.fetchall()
                    if row[1] is not None
                ]

                return jsonify({"data": data, "period": period})

    except Exception:
        app.logger.exception("Stock history API error")
        return jsonify({"error": "Could not load price history"}), 500


if __name__ == "__main__":
    app.run(debug=True)
