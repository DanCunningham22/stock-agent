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
    "value": 0.18,
    "growth": 0.18,
    "quality": 0.14,
    "momentum": 0.14,
    "bounce": 0.08,
    "analyst": 0.08,
    "liquidity": 0.10,
    "volatility": 0.10,
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
    import pandas as pd
    df = pd.read_csv("tools/universe.csv")
    return df["ticker"].dropna().unique().tolist()

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
    return (series - series.mean()) / (series.std() + 1e-9)


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

        # VOLATILITY (penalty)
        volatility = df["Close"].pct_change().std()
        volatility_raw = -volatility

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
            "volatility_raw": volatility_raw,
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
        "volatility_raw",
    ]:
        df_scores[col.replace("_raw", "_score")] = normalize(df_scores[col])

    df_scores["total_score"] = (
        df_scores["value_score"] * FACTOR_WEIGHTS["value"] +
        df_scores["growth_score"] * FACTOR_WEIGHTS["growth"] +
        df_scores["quality_score"] * FACTOR_WEIGHTS["quality"] +
        df_scores["momentum_score"] * FACTOR_WEIGHTS["momentum"] +
        df_scores["bounce_score"] * FACTOR_WEIGHTS["bounce"] +
        df_scores["analyst_score"] * FACTOR_WEIGHTS["analyst"] +
        df_scores["liquidity_score"] * FACTOR_WEIGHTS["liquidity"] +
        df_scores["volatility_score"] * FACTOR_WEIGHTS["volatility"]
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

    # -------------------------------------------------
    # Rank buffer logic (reduces turnover)
    # -------------------------------------------------

    conn2 = sqlite3.connect(DB_NAME)

    yesterday = (dt.date.today() - dt.timedelta(days=1)).isoformat()

    prev_df = pd.read_sql(
        f"""
        SELECT ticker, rank as previous_rank
        FROM daily_scores
        WHERE date = '{yesterday}'
        """,
        conn2
    )

    conn2.close()

    if not prev_df.empty:
        prev_top = prev_df.sort_values("previous_rank").head(TOP_N)["ticker"].tolist()
        df_scores["was_in_portfolio"] = df_scores["ticker"].isin(prev_top)
    else:
        df_scores["was_in_portfolio"] = False

    # Entry: rank <= 15
    # Exit: keep if rank <= 30 AND was already held
    buffered = df_scores[
        (df_scores["rank"] <= 15) |
        ((df_scores["rank"] <= 30) & (df_scores["was_in_portfolio"]))
    ]

    top = buffered.sort_values("rank").head(TOP_N)


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

def backtest_portfolio(days_forward=60):

    conn = sqlite3.connect(DB_NAME)
    today = str(dt.date.today())

    portfolio = pd.read_sql(
        f"SELECT ticker FROM portfolio_history WHERE date = '{today}'",
        conn
    )
    conn.close()

    tickers = portfolio["ticker"].tolist()

    if not tickers:
        return None

    data = yf.download(tickers + ["SPY"], period=f"{days_forward}d", progress=False)["Close"]

    returns = data.pct_change().dropna()

    portfolio_returns = returns[tickers].mean(axis=1)
    spy_returns = returns["SPY"]

    cumulative = (1 + portfolio_returns).cumprod()
    spy_cumulative = (1 + spy_returns).cumprod()

    sharpe = portfolio_returns.mean() / (portfolio_returns.std() + 1e-9) * (252**0.5)
    drawdown = (cumulative / cumulative.cummax() - 1).min()
    alpha = cumulative.iloc[-1] - spy_cumulative.iloc[-1]

    return {
        "total_return": cumulative.iloc[-1] - 1,
        "spy_return": spy_cumulative.iloc[-1] - 1,
        "alpha": alpha,
        "sharpe": sharpe,
        "max_drawdown": drawdown,
    }


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

    # ----------------------------------------------------------
    # Rank Change vs Yesterday
    # ----------------------------------------------------------

    conn = sqlite3.connect(DB_NAME)

    yesterday = (dt.date.today() - dt.timedelta(days=1)).isoformat()

    prev_df = pd.read_sql(
        f"""
        SELECT ticker, rank as previous_rank
        FROM daily_scores
        WHERE date = '{yesterday}'
        """,
        conn
    )

    conn.close()

    if not prev_df.empty:
        df_scores = df_scores.merge(prev_df, on="ticker", how="left")
        df_scores["rank_change"] = df_scores["previous_rank"] - df_scores["rank"]
    else:
        df_scores["previous_rank"] = None
        df_scores["rank_change"] = None

    print("\nTop 20 Portfolio:")
    print(df_scores.head(TOP_N)[["ticker", "total_score", "rank", "rank_change"]])

    return df_scores.head(TOP_N)



# ============================================================
# MANUAL RUN
# ============================================================

if __name__ == "__main__":
    run_daily_model()