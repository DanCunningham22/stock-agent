import yfinance as yf
from models import StockData
from datetime import date


def get_stock_data(ticker: str) -> StockData:
    """Fetch current stock price, fundamentals, short interest, analyst targets."""
    stock = yf.Ticker(ticker)
    info = stock.info

    return StockData(
        ticker=ticker,
        price=info.get("currentPrice", info.get("regularMarketPrice", 0)),
        market_cap=info.get("marketCap", 0),
        pe_ratio=info.get("trailingPE"),
        forward_pe=info.get("forwardPE"),
        revenue_ttm=info.get("totalRevenue"),
        earnings_ttm=info.get("netIncomeToCommon"),
        debt_to_equity=info.get("debtToEquity"),
        dividend_yield=info.get("dividendYield"),
        fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
        fifty_two_week_low=info.get("fiftyTwoWeekLow"),
        beta=info.get("beta"),
        short_percent_of_float=info.get("shortPercentOfFloat"),
        avg_volume=info.get("averageVolume"),
        current_volume=info.get("volume"),
        analyst_target_price=info.get("targetMeanPrice"),
        analyst_recommendation=info.get("recommendationKey"),
        number_of_analysts=info.get("numberOfAnalystOpinions"),
        sector=info.get("sector", "Unknown"),
        industry=info.get("industry", "Unknown"),
        company_name=info.get("longName", info.get("shortName", ticker)),
        fetch_date=date.today(),
    )


def get_financial_statements(ticker: str) -> dict:
    stock = yf.Ticker(ticker)
    def safe_to_dict(df):
        if df is not None and not df.empty:
            return df.to_dict()
        return {}
    return {
        "income_statement": safe_to_dict(stock.financials),
        "balance_sheet": safe_to_dict(stock.balance_sheet),
        "cash_flow": safe_to_dict(stock.cashflow),
    }


def get_price_history(ticker: str, period: str = "1y") -> dict:
    stock = yf.Ticker(ticker)
    hist = stock.history(period=period)

    if hist.empty:
        return {"ticker": ticker, "error": "No price data available"}

    prices = hist["Close"].tolist()
    volumes = hist["Volume"].tolist()

    avg_volume_30d = sum(volumes[-30:]) / min(len(volumes), 30) if volumes else 0
    current_volume = volumes[-1] if volumes else 0

    sma_50 = sum(prices[-50:]) / min(len(prices), 50) if len(prices) >= 50 else None
    sma_200 = sum(prices[-200:]) / min(len(prices), 200) if len(prices) >= 200 else None

    pct_1d = ((prices[-1] - prices[-2]) / prices[-2] * 100) if len(prices) >= 2 else None
    pct_1w = ((prices[-1] - prices[-5]) / prices[-5] * 100) if len(prices) >= 5 else None
    pct_1m = ((prices[-1] - prices[-21]) / prices[-21] * 100) if len(prices) >= 21 else None
    pct_3m = ((prices[-1] - prices[-63]) / prices[-63] * 100) if len(prices) >= 63 else None

    return {
        "ticker": ticker,
        "period": period,
        "data_points": len(prices),
        "current": round(prices[-1], 2),
        "period_high": round(max(prices), 2),
        "period_low": round(min(prices), 2),
        "period_avg": round(sum(prices) / len(prices), 2),
        "period_start": round(prices[0], 2),
        "pct_change_total": round((prices[-1] - prices[0]) / prices[0] * 100, 2),
        "pct_change_1d": round(pct_1d, 2) if pct_1d else None,
        "pct_change_1w": round(pct_1w, 2) if pct_1w else None,
        "pct_change_1m": round(pct_1m, 2) if pct_1m else None,
        "pct_change_3m": round(pct_3m, 2) if pct_3m else None,
        "sma_50": round(sma_50, 2) if sma_50 else None,
        "sma_200": round(sma_200, 2) if sma_200 else None,
        "above_sma_50": prices[-1] > sma_50 if sma_50 else None,
        "above_sma_200": prices[-1] > sma_200 if sma_200 else None,
        "current_volume": int(current_volume),
        "avg_volume_30d": int(avg_volume_30d),
        "volume_ratio": round(current_volume / avg_volume_30d, 2) if avg_volume_30d else None,
        "start_date": str(hist.index[0].date()),
        "end_date": str(hist.index[-1].date()),
    }


def get_insider_trades(ticker: str) -> list[dict]:
    stock = yf.Ticker(ticker)
    try:
        insiders = stock.insider_transactions
        if insiders is None or insiders.empty:
            return [{"message": "No recent insider transactions found"}]
        trades = []
        for _, row in insiders.head(15).iterrows():
            trades.append({
                "insider": str(row.get("Insider", "Unknown")),
                "title": str(row.get("Position", row.get("Title", "Unknown"))),
                "type": str(row.get("Transaction", row.get("Text", "Unknown"))),
                "shares": int(row.get("Shares", 0)) if row.get("Shares") else 0,
                "value": float(row.get("Value", 0)) if row.get("Value") else 0,
                "date": str(row.get("Start Date", row.get("Date", "Unknown"))),
            })
        return trades
    except Exception as e:
        return [{"error": f"Could not fetch insider data: {e}"}]


def get_analyst_estimates(ticker: str) -> dict:
    stock = yf.Ticker(ticker)
    result = {}
    try:
        rec = stock.recommendations
        if rec is not None and not rec.empty:
            result["recent_recommendations"] = rec.tail(10).to_dict(orient="records")
    except:
        result["recent_recommendations"] = []
    try:
        estimates = stock.earnings_estimate
        if estimates is not None and not estimates.empty:
            result["earnings_estimates"] = estimates.to_dict()
    except:
        result["earnings_estimates"] = {}
    info = stock.info
    result["target_high"] = info.get("targetHighPrice")
    result["target_low"] = info.get("targetLowPrice")
    result["target_mean"] = info.get("targetMeanPrice")
    result["target_median"] = info.get("targetMedianPrice")
    result["recommendation"] = info.get("recommendationKey")
    result["num_analysts"] = info.get("numberOfAnalystOpinions")
    return result


def get_macro_data() -> dict:
    result = {}
    try:
        spy = yf.Ticker("SPY")
        spy_hist = spy.history(period="5d")
        if not spy_hist.empty:
            prices = spy_hist["Close"].tolist()
            result["sp500_price"] = round(prices[-1], 2)
            if len(prices) >= 2:
                result["sp500_change_pct"] = round((prices[-1] - prices[-2]) / prices[-2] * 100, 2)
    except:
        pass
    try:
        vix = yf.Ticker("^VIX")
        vix_hist = vix.history(period="5d")
        if not vix_hist.empty:
            result["vix"] = round(vix_hist["Close"].tolist()[-1], 2)
    except:
        pass
    try:
        tnx = yf.Ticker("^TNX")
        tnx_hist = tnx.history(period="5d")
        if not tnx_hist.empty:
            result["ten_year_yield"] = round(tnx_hist["Close"].tolist()[-1], 2)
    except:
        pass
    result["fetch_date"] = str(date.today())
    return result


def get_sector_performance(sector_etf: str = None) -> dict:
    sector_etfs = {
        "Technology": "XLK", "Healthcare": "XLV", "Financial": "XLF",
        "Consumer Cyclical": "XLY", "Consumer Defensive": "XLP",
        "Energy": "XLE", "Industrials": "XLI", "Communication Services": "XLC",
        "Real Estate": "XLRE", "Materials": "XLB", "Utilities": "XLU",
    }
    results = {}
    etfs_to_check = {sector_etf: sector_etf} if sector_etf else sector_etfs
    for name, etf in etfs_to_check.items():
        try:
            ticker = yf.Ticker(etf)
            hist = ticker.history(period="1mo")
            if not hist.empty:
                prices = hist["Close"].tolist()
                results[name] = {
                    "etf": etf,
                    "current": round(prices[-1], 2),
                    "pct_change_1mo": round((prices[-1] - prices[0]) / prices[0] * 100, 2),
                }
        except:
            pass
    return results
