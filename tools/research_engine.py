import yfinance as yf
import pandas as pd
import requests
import sqlite3
import datetime as dt
import numpy as np
from io import StringIO
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================================
# CONFIG
# ============================================================

DB_NAME = "screener.db"
TOP_N = 20
MIN_PRICE = 5
MIN_VOLUME = 500_000

FACTOR_WEIGHTS = {
    "value": 0.20,
    "growth": 0.20,
    "quality": 0.15,
    "momentum": 0.15,
    "bounce": 0.10,
    "analyst": 0.10,
    "liquidity": 0.10,
}

# ============================================================
# DATABASE SETUP
# ============================================================

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS daily_scores (
        date TEXT,
        ticker TEXT,
        total_score REAL,
        value_score REAL,
        growth_score REAL,
        quality_score REAL,
        momentum_score REAL,
        bounce_score REAL,
        analyst_score REAL,
        liquidity_score REAL,
        price REAL,
        rank INTEGER
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS portfolio_history (
        date TEXT,
        ticker TEXT,
        rank INTEGER,
        weight REAL
    )
    """)

    conn.commit()
    conn.close()


# ============================================================
# UNIVERSE
# ============================================================

def get_all_us_stocks():
    urls = {
        "nasdaq": "https://ftp.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
        "other": "https://ftp.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
    }

    all_tickers = []

    for name, url in urls.items():
        response = requests.get(url)
        df = pd.read_csv(StringIO(response.text), sep="|")
        df = df[df["Symbol"] != "File Creation Time"]

        if name == "nasdaq":
            df = df[df["ETF"] == "N"]
            tickers = df["Symbol"].tolist()
        else:
            df = df[df["ETF"] == "N"]
            tickers = df["ACT Symbol"].tolist()

        all_tickers.extend(tickers)

    return sorted(set(all_tickers))


# ============================================================
# LIQUIDITY FILTER
# ============================================================

def filter_liquid_stocks(tickers):
    batch = yf.download(
        tickers,
        period="6mo",
        group_by="ticker",
        threads=True,
        progress=False,
    )

    valid = []
    price_data = {}

    for ticker in tickers:
        try:
            df = batch[ticker]
            if df.empty:
                continue

            price = df["Close"].iloc[-1]
            avg_vol = df["Volume"].mean()

            if price > MIN_PRICE and avg_vol > MIN_VOLUME:
                valid.append(ticker)
                price_data[ticker] = df

        except:
            continue

    return valid, price_data


# ============================================================
# FUNDAMENTALS
# ============================================================

def fetch_fundamental(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        if not info:
            return None

        return {
            "ticker": ticker,
            "pe": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "profit_margin": info.get("profitMargins"),
            "debt_to_equity": info.get("debtToEquity"),
            "analyst_target": info.get("targetMeanPrice"),
        }
    except:
        return None


def fetch_all_fundamentals(tickers):
    results = {}

    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = [executor.submit(fetch_fundamental, t) for t in tickers]

        for future in as_completed(futures):
            data = future.result()
            if data:
                results[data["ticker"]] = data

    return results


# ============================================================
# FACTOR SCORING
# ============================================================

def normalize(series):
    return (series - series.min()) / (series.max() - series.min() + 1e-9) * 100


def compute_scores(valid_tickers, price_data, fundamentals):

    rows = []

    for ticker in valid_tickers:
        if ticker not in fundamentals:
            continue

        f = fundamentals[ticker]
        df = price_data[ticker]
        price = df["Close"].iloc[-1]

        # VALUE
        pe = f.get("pe")
        value_raw = 1 / pe if pe and pe > 0 else 0

        # GROWTH
        growth_raw = f.get("revenue_growth") or 0

        # QUALITY
        margin = f.get("profit_margin") or 0
        debt = f.get("debt_to_equity") or 100
        quality_raw = margin - (debt / 1000)

        # MOMENTUM (6M return)
        ret_6m = (df["Close"].iloc[-1] / df["Close"].iloc[0]) - 1

        # BOUNCE
        high = df["High"].max()
        low = df["Low"].min()
        bounce_raw = (price - low) / (high - low + 1e-9)

        # ANALYST
        target = f.get("analyst_target")
        analyst_raw = ((target - price) / price) if target else 0

        # LIQUIDITY
        liquidity_raw = df["Volume"].mean()

        rows.append({
            "ticker": ticker,
            "price": price,
            "value_raw": value_raw,
            "growth_raw": growth_raw,
            "quality_raw": quality_raw,
            "momentum_raw": ret_6m,
            "bounce_raw": bounce_raw,
            "analyst_raw": analyst_raw,
            "liquidity_raw": liquidity_raw,
        })

    df_scores = pd.DataFrame(rows)

    for col in [
        "value_raw",
        "growth_raw",
        "quality_raw",
        "momentum_raw",
        "bounce_raw",
        "analyst_raw",
        "liquidity_raw",
    ]:
        df_scores[col.replace("_raw", "_score")] = normalize(df_scores[col])

    df_scores["total_score"] = (
        df_scores["value_score"] * FACTOR_WEIGHTS["value"] +
        df_scores["growth_score"] * FACTOR_WEIGHTS["growth"] +
        df_scores["quality_score"] * FACTOR_WEIGHTS["quality"] +
        df_scores["momentum_score"] * FACTOR_WEIGHTS["momentum"] +
        df_scores["bounce_score"] * FACTOR_WEIGHTS["bounce"] +
        df_scores["analyst_score"] * FACTOR_WEIGHTS["analyst"] +
        df_scores["liquidity_score"] * FACTOR_WEIGHTS["liquidity"]
    )

    df_scores = df_scores.sort_values("total_score", ascending=False)
    df_scores["rank"] = range(1, len(df_scores) + 1)

    return df_scores


# ============================================================
# PERSISTENCE
# ============================================================

def save_daily_scores(df_scores):
    today = str(dt.date.today())
    conn = sqlite3.connect(DB_NAME)

    df_scores_to_save = df_scores.copy()
    df_scores_to_save["date"] = today

    df_scores_to_save[[
        "date",
        "ticker",
        "total_score",
        "value_score",
        "growth_score",
        "quality_score",
        "momentum_score",
        "bounce_score",
        "analyst_score",
        "liquidity_score",
        "price",
        "rank"
    ]].to_sql("daily_scores", conn, if_exists="append", index=False)

    conn.close()


def save_portfolio(df_scores):
    today = str(dt.date.today())
    conn = sqlite3.connect(DB_NAME)

    top = df_scores.head(TOP_N)

    portfolio = pd.DataFrame({
        "date": today,
        "ticker": top["ticker"],
        "rank": top["rank"],
        "weight": 1 / TOP_N
    })

    portfolio.to_sql("portfolio_history", conn, if_exists="append", index=False)
    conn.close()


# ============================================================
# BACKTEST
# ============================================================

def backtest_portfolio(days_forward=30):
    conn = sqlite3.connect(DB_NAME)
    today = str(dt.date.today())

    portfolio = pd.read_sql(
        f"SELECT ticker FROM portfolio_history WHERE date = '{today}'",
        conn
    )

    conn.close()

    tickers = portfolio["ticker"].tolist()

    data = yf.download(tickers, period=f"{days_forward}d", progress=False)

    returns = []
    for ticker in tickers:
        try:
            start = data["Close"][ticker].iloc[0]
            end = data["Close"][ticker].iloc[-1]
            returns.append((end / start) - 1)
        except:
            continue

    return np.mean(returns)


# ============================================================
# MAIN RUNNER
# ============================================================

def run_daily_model():

    init_db()

    print("Loading universe...")
    universe = get_all_us_stocks()

    print("Applying liquidity filter...")
    valid, price_data = filter_liquid_stocks(universe)

    print(f"Liquid stocks: {len(valid)}")

    print("Fetching fundamentals...")
    fundamentals = fetch_all_fundamentals(valid)

    print("Computing scores...")
    df_scores = compute_scores(valid, price_data, fundamentals)

    print("Saving results...")
    save_daily_scores(df_scores)
    save_portfolio(df_scores)

    print("\nTop 20 Portfolio:")
    print(df_scores.head(TOP_N)[["ticker", "total_score", "rank"]])

    return df_scores.head(TOP_N)


# ============================================================
# MANUAL RUN
# ============================================================

if __name__ == "__main__":
    run_daily_model()