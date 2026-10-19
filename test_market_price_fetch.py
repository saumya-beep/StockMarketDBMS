import math
import time
import yfinance as yf
from import_market_data import STOCKS

def main():
    print("Testing Yahoo Finance price retrieval")
    print("No database changes will be made.\n")

    successful = 0
    failed = []

    for symbol, ticker, company, sector in STOCKS:
        try:
            data = yf.Ticker(ticker).history(
                period="5d",
                interval="1d",
                auto_adjust=False
            )

            if data.empty or "Close" not in data.columns:
                failed.append((symbol, "No price data returned"))
                continue

            closes = data["Close"].dropna()
            if closes.empty:
                failed.append((symbol, "No valid closing price"))
                continue

            price = float(closes.iloc[-1])

            if not math.isfinite(price) or price <= 0:
                failed.append((symbol, "Invalid price"))
                continue

            date = closes.index[-1]
            print(f"{symbol:12} ₹{price:10.2f}  Latest daily close: {date}")
            successful += 1

            time.sleep(0.1)

        except Exception as exc:
            failed.append((symbol, str(exc)[:120]))

    print(f"\nSuccessful: {successful}/{len(STOCKS)}")
    print(f"Failed: {len(failed)}")

    if failed:
        print("\nSymbols needing attention:")
        for symbol, reason in failed:
            print(f"- {symbol}: {reason}")

    print("\nTest complete. Oracle was not modified.")

if __name__ == "__main__":
    main()
