import math
import sys
import time
from datetime import datetime

import yfinance as yf
from db import get_connection
from import_market_data import STOCKS


def fetch_latest_price(ticker):
    data = yf.Ticker(ticker).history(
        period="5d",
        interval="1d",
        auto_adjust=False
    )

    if data.empty or "Close" not in data.columns:
        return None

    closes = data["Close"].dropna()
    if closes.empty:
        return None

    price = float(closes.iloc[-1])

    if not math.isfinite(price) or price <= 0:
        return None

    return price


def main():
    print("Fetching latest available daily closing prices...")
    print("Oracle will be updated only after fetching is complete.\n")

    prices = {}
    failed = []

    # Fetch first; do not modify Oracle during this phase.
    for symbol, ticker, company, sector in STOCKS:
        try:
            price = fetch_latest_price(ticker)

            if price is None:
                failed.append(symbol)
                print(f"SKIPPED {symbol}: no valid price returned")
            else:
                prices[symbol] = price
                print(f"OK      {symbol}: Rs. {price:.2f}")

        except Exception as exc:
            failed.append(symbol)
            print(f"SKIPPED {symbol}: {str(exc)[:100]}")

        time.sleep(0.2)

    if not prices:
        print("\nNo valid prices were fetched. Oracle was not changed.")
        return

    print(f"\nFetched: {len(prices)}/{len(STOCKS)}")
    print(f"Skipped: {len(failed)}")

    if "--yes" in sys.argv:
        confirm = "YES"
        print("Automatic confirmation enabled.")
    else:
        confirm = input(
            "\nUpdate STOCK.CURRENT_PRICE with these prices? Type YES to continue: "
        ).strip()

    if confirm != "YES":
        print("Cancelled. Oracle was not changed.")
        return

    conn = None
    cur = None

    try:
        conn = get_connection()
        cur = conn.cursor()

        # Confirm every symbol exists before changing any price.
        cur.execute("SELECT SYMBOL FROM STOCK")
        existing = {row[0].upper() for row in cur.fetchall()}

        missing = [s for s in prices if s.upper() not in existing]
        if missing:
            raise RuntimeError(
                "Symbols missing from Oracle STOCK table: "
                + ", ".join(missing)
            )

        for symbol, price in prices.items():
            cur.execute(
                """
                UPDATE STOCK
                SET CURRENT_PRICE = :price
                WHERE UPPER(SYMBOL) = :symbol
                """,
                {"price": price, "symbol": symbol.upper()}
            )

            if cur.rowcount != 1:
                raise RuntimeError(
                    f"Expected one row for {symbol}; got {cur.rowcount}"
                )

        conn.commit()

        print("\nPrice refresh committed successfully.")
        print("Stocks updated:", len(prices))
        print("Failed symbols left unchanged:", len(failed))
        print("Update completed at:", datetime.now().astimezone().isoformat())
        print("Historical price records were not modified.")

    except Exception:
        if conn is not None:
            conn.rollback()
        print("\nUpdate failed. Database changes were rolled back.")
        raise

    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()

