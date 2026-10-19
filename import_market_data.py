import math
import time
import pandas as pd
import yfinance as yf
from db import get_connection

# Database symbol, Yahoo symbol, company name, sector
STOCKS = [
    ("TCS","TCS.NS","Tata Consultancy Services","IT"),
    ("INFY","INFY.NS","Infosys Limited","IT"),
    ("HDFCBANK","HDFCBANK.NS","HDFC Bank","Banking"),
    ("RELIANCE","RELIANCE.NS","Reliance Industries","Energy"),
    ("ICICIBANK","ICICIBANK.NS","ICICI Bank","Banking"),
    ("SBIN","SBIN.NS","State Bank of India","Banking"),
    ("AXISBANK","AXISBANK.NS","Axis Bank","Banking"),
    ("KOTAKBANK","KOTAKBANK.NS","Kotak Mahindra Bank","Banking"),
    ("INDUSINDBK","INDUSINDBK.NS","IndusInd Bank","Banking"),
    ("BAJFINANCE","BAJFINANCE.NS","Bajaj Finance","Finance"),
    ("BAJAJFINSV","BAJAJFINSV.NS","Bajaj Finserv","Finance"),
    ("HDFCLIFE","HDFCLIFE.NS","HDFC Life Insurance","Insurance"),
    ("SBILIFE","SBILIFE.NS","SBI Life Insurance","Insurance"),
    ("ICICIPRULI","ICICIPRULI.NS","ICICI Prudential Life Insurance","Insurance"),
    ("LT","LT.NS","Larsen and Toubro","Infrastructure"),
    ("LTIM","LTIM.NS","LTIMindtree","IT"),
    ("WIPRO","WIPRO.NS","Wipro","IT"),
    ("HCLTECH","HCLTECH.NS","HCL Technologies","IT"),
    ("TECHM","TECHM.NS","Tech Mahindra","IT"),
    ("PERSISTENT","PERSISTENT.NS","Persistent Systems","IT"),
    ("COFORGE","COFORGE.NS","Coforge","IT"),
    ("MPHASIS","MPHASIS.NS","Mphasis","IT"),
    ("OFSS","OFSS.NS","Oracle Financial Services Software","IT"),
    ("TATAELXSI","TATAELXSI.NS","Tata Elxsi","IT"),
    ("BHARTIARTL","BHARTIARTL.NS","Bharti Airtel","Telecom"),
    ("IDEA","IDEA.NS","Vodafone Idea","Telecom"),
    ("TATACOMM","TATACOMM.NS","Tata Communications","Telecom"),
    ("ITC","ITC.NS","ITC Limited","FMCG"),
    ("HINDUNILVR","HINDUNILVR.NS","Hindustan Unilever","FMCG"),
    ("NESTLEIND","NESTLEIND.NS","Nestle India","FMCG"),
    ("BRITANNIA","BRITANNIA.NS","Britannia Industries","FMCG"),
    ("DABUR","DABUR.NS","Dabur India","FMCG"),
    ("GODREJCP","GODREJCP.NS","Godrej Consumer Products","FMCG"),
    ("MARICO","MARICO.NS","Marico","FMCG"),
    ("TATACONSUM","TATACONSUM.NS","Tata Consumer Products","FMCG"),
    ("ASIANPAINT","ASIANPAINT.NS","Asian Paints","Consumer"),
    ("BERGEPAINT","BERGEPAINT.NS","Berger Paints India","Consumer"),
    ("PIDILITIND","PIDILITIND.NS","Pidilite Industries","Consumer"),
    ("TITAN","TITAN.NS","Titan Company","Consumer"),
    ("TRENT","TRENT.NS","Trent Limited","Retail"),
    ("DMART","DMART.NS","Avenue Supermarts","Retail"),
    ("JUBLFOOD","JUBLFOOD.NS","Jubilant FoodWorks","Retail"),
    ("MARUTI","MARUTI.NS","Maruti Suzuki India","Automobile"),
    ("TATAMOTORS","TATAMOTORS.NS","Tata Motors","Automobile"),
    ("M&M","M&M.NS","Mahindra and Mahindra","Automobile"),
    ("HEROMOTOCO","HEROMOTOCO.NS","Hero MotoCorp","Automobile"),
    ("EICHERMOT","EICHERMOT.NS","Eicher Motors","Automobile"),
    ("TVSMOTOR","TVSMOTOR.NS","TVS Motor Company","Automobile"),
    ("BAJAJ-AUTO","BAJAJ-AUTO.NS","Bajaj Auto","Automobile"),
    ("SUNPHARMA","SUNPHARMA.NS","Sun Pharmaceutical Industries","Pharma"),
    ("DRREDDY","DRREDDY.NS","Dr Reddys Laboratories","Pharma"),
    ("CIPLA","CIPLA.NS","Cipla","Pharma"),
    ("DIVISLAB","DIVISLAB.NS","Divis Laboratories","Pharma"),
    ("APOLLOHOSP","APOLLOHOSP.NS","Apollo Hospitals Enterprise","Healthcare"),
    ("LUPIN","LUPIN.NS","Lupin","Pharma"),
    ("AUROPHARMA","AUROPHARMA.NS","Aurobindo Pharma","Pharma"),
    ("ONGC","ONGC.NS","Oil and Natural Gas Corporation","Energy"),
    ("NTPC","NTPC.NS","NTPC Limited","Power"),
    ("POWERGRID","POWERGRID.NS","Power Grid Corporation of India","Power"),
    ("TATAPOWER","TATAPOWER.NS","Tata Power","Power"),
    ("ADANIPORTS","ADANIPORTS.NS","Adani Ports and Special Economic Zone","Infrastructure"),
    ("ADANIENT","ADANIENT.NS","Adani Enterprises","Infrastructure"),
    ("ULTRACEMCO","ULTRACEMCO.NS","UltraTech Cement","Cement"),
    ("GRASIM","GRASIM.NS","Grasim Industries","Cement"),
    ("SHREECEM","SHREECEM.NS","Shree Cement","Cement"),
    ("JSWSTEEL","JSWSTEEL.NS","JSW Steel","Metals"),
    ("TATASTEEL","TATASTEEL.NS","Tata Steel","Metals"),
    ("HINDALCO","HINDALCO.NS","Hindalco Industries","Metals"),
    ("COALINDIA","COALINDIA.NS","Coal India","Energy"),
    ("IOC","IOC.NS","Indian Oil Corporation","Energy"),
    ("BPCL","BPCL.NS","Bharat Petroleum Corporation","Energy"),
    ("GAIL","GAIL.NS","GAIL India","Energy"),
    ("ZOMATO","ETERNAL.NS","Eternal Limited","Retail"),
    ("IRCTC","IRCTC.NS","Indian Railway Catering and Tourism Corporation","Travel"),
    ("HAL","HAL.NS","Hindustan Aeronautics","Aerospace"),
    ("BEL","BEL.NS","Bharat Electronics","Aerospace"),
]

def valid_number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None

def main():
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Create any missing sectors.
        cur.execute("SELECT SECTOR_NAME, SECTOR_ID FROM MARKET_SECTOR")
        sectors = {name.upper(): sid for name, sid in cur.fetchall()}

        for _, _, _, sector in STOCKS:
            if sector.upper() not in sectors:
                cur.execute(
                    "SELECT NVL(MAX(SECTOR_ID), 0) + 1 FROM MARKET_SECTOR"
                )
                sid = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO MARKET_SECTOR (SECTOR_ID, SECTOR_NAME) "
                    "VALUES (:1, :2)",
                    [sid, sector]
                )
                sectors[sector.upper()] = sid

        conn.commit()

        # Add missing companies and stocks; retain existing IDs.
        cur.execute("SELECT SYMBOL, STOCK_ID FROM STOCK")
        existing_stocks = {s.upper(): i for s, i in cur.fetchall()}

        cur.execute("SELECT COMPANY_NAME, COMPANY_ID FROM COMPANY")
        existing_companies = {n.upper(): i for n, i in cur.fetchall()}

        for symbol, _, company, sector in STOCKS:
            if symbol.upper() in existing_stocks:
                continue

            company_id = existing_companies.get(company.upper())

            if company_id is None:
                cur.execute("SELECT NVL(MAX(COMPANY_ID), 0) + 1 FROM COMPANY")
                company_id = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO COMPANY "
                    "(COMPANY_ID, COMPANY_NAME, SECTOR_ID) "
                    "VALUES (:1, :2, :3)",
                    [company_id, company, sectors[sector.upper()]]
                )
                existing_companies[company.upper()] = company_id

            cur.execute("SELECT NVL(MAX(STOCK_ID), 0) + 1 FROM STOCK")
            stock_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO STOCK "
                "(STOCK_ID, SYMBOL, CURRENT_PRICE, FACE_VALUE, COMPANY_ID) "
                "VALUES (:1, :2, 0, 1, :3)",
                [stock_id, symbol, company_id]
            )
            existing_stocks[symbol.upper()] = stock_id

        conn.commit()
        print("Stock catalogue prepared:", len(existing_stocks), "stocks")

        # Fetch one year of daily historical market data.
        tickers = [item[1] for item in STOCKS]
        print("Downloading daily historical data. Please wait...")

        data = yf.download(
            tickers,
            period="1y",
            interval="1d",
            group_by="ticker",
            auto_adjust=False,
            threads=True,
            progress=False
        )

        if data is None or data.empty:
            raise RuntimeError(
                "No market data was returned. Check internet access "
                "and try again later."
            )

        successful = 0
        failed = []
        total_records = 0

        for symbol, ticker, company, sector in STOCKS:
            try:
                # Handle yfinance column layout variations.
                if isinstance(data.columns, pd.MultiIndex):
                    if ticker in data.columns.get_level_values(0):
                        hist = data[ticker].copy()
                    elif ticker in data.columns.get_level_values(1):
                        hist = data.xs(ticker, axis=1, level=1).copy()
                    else:
                        failed.append((symbol, "No data returned"))
                        continue
                else:
                    hist = data.copy() if len(tickers) == 1 else pd.DataFrame()

                if hist.empty or "Close" not in hist.columns:
                    failed.append((symbol, "No usable history"))
                    continue

                stock_id = existing_stocks[symbol.upper()]

                # Do not duplicate history on a rerun.
                cur.execute(
                    "SELECT COUNT(*) FROM STOCK_PRICE_HISTORY "
                    "WHERE STOCK_ID = :1 AND INTERVAL_TYPE = '1d' "
                    "AND DATA_SOURCE = 'Yahoo Finance (yfinance)'",
                    [stock_id]
                )
                if cur.fetchone()[0] > 0:
                    print(symbol, "history already exists; skipped")
                    continue

                rows = []
                for dt, row in hist.iterrows():
                    close = valid_number(row.get("Close"))
                    if close is None or close <= 0:
                        continue

                    op = valid_number(row.get("Open"))
                    hi = valid_number(row.get("High"))
                    lo = valid_number(row.get("Low"))
                    vol = valid_number(row.get("Volume"))

                    timestamp = pd.Timestamp(dt).to_pydatetime()
                    timestamp = timestamp.replace(tzinfo=None)

                    rows.append((
                        None, stock_id, round(close, 2), timestamp,
                        round(op, 2) if op is not None else None,
                        round(hi, 2) if hi is not None else None,
                        round(lo, 2) if lo is not None else None,
                        round(close, 2),
                        int(vol) if vol is not None else None,
                        "1d", "Yahoo Finance (yfinance)"
                    ))

                if not rows:
                    failed.append((symbol, "No valid daily prices"))
                    continue

                cur.executemany(
                    "INSERT INTO STOCK_PRICE_HISTORY "
                    "(PRICE_ID, STOCK_ID, PRICE, RECORDED_AT, "
                    "OPEN_PRICE, HIGH_PRICE, LOW_PRICE, CLOSE_PRICE, "
                    "VOLUME, INTERVAL_TYPE, DATA_SOURCE) "
                    "VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11)",
                    rows
                )

                latest_close = rows[-1][7]
                cur.execute(
                    "UPDATE STOCK SET CURRENT_PRICE = :1 "
                    "WHERE STOCK_ID = :2",
                    [latest_close, stock_id]
                )

                conn.commit()
                successful += 1
                total_records += len(rows)
                print(symbol, "-", len(rows), "daily records imported")

                time.sleep(0.15)

            except Exception as exc:
                conn.rollback()
                failed.append((symbol, str(exc)[:180]))
                print("Failed:", symbol, str(exc)[:180])

        print("\nImport finished.")
        print("Stocks with newly imported history:", successful)
        print("Historical records imported:", total_records)
        print("Stocks with errors or unavailable data:", len(failed))

        for symbol, reason in failed:
            print(" -", symbol, ":", reason)

        cur.execute("SELECT COUNT(*) FROM STOCK")
        print("Total stocks in Oracle:", cur.fetchone()[0])

        cur.execute("SELECT COUNT(*) FROM STOCK_PRICE_HISTORY")
        print("Total price-history records:", cur.fetchone()[0])

    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
