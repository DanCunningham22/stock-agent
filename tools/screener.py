import yfinance as yf
import requests


# Pre-built lists of popular stocks by sector
STOCK_UNIVERSE = {
    "Technology": [
        "AAPL", "MSFT", "GOOGL", "META", "NVDA", "TSLA", "AVGO", "ADBE", "CRM", "AMD",
        "INTC", "ORCL", "CSCO", "QCOM", "TXN", "NOW", "IBM", "AMAT", "MU", "LRCX",
        "KLAC", "SNPS", "CDNS", "MRVL", "FTNT", "PANW", "CRWD", "ZS", "DDOG", "NET",
        "SNOW", "PLTR", "SHOP", "SQ", "COIN", "HOOD", "MSTR", "RBLX", "U", "TWLO",
    ],
    "Healthcare": [
        "UNH", "JNJ", "LLY", "PFE", "ABBV", "MRK", "TMO", "ABT", "DHR", "BMY",
        "AMGN", "GILD", "ISRG", "CVS", "ELV", "CI", "SYK", "BSX", "VRTX", "REGN",
        "ZTS", "HUM", "IDXX", "DXCM", "MRNA", "BIIB", "ILMN", "ALGN", "HOLX", "IQV",
    ],
    "Financial": [
        "BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "SCHW", "BLK",
        "C", "AXP", "SPGI", "CME", "ICE", "AON", "MMC", "PGR", "TRV", "CB",
        "MET", "AIG", "PRU", "ALL", "AFL", "FIS", "FISV", "SQ", "PYPL", "SOFI",
    ],
    "Consumer": [
        "AMZN", "HD", "MCD", "NKE", "SBUX", "TGT", "COST", "WMT", "LOW", "TJX",
        "BKNG", "MAR", "HLT", "CMG", "YUM", "DPZ", "LULU", "ROST", "DG", "DLTR",
        "F", "GM", "TSLA", "RIVN", "LCID", "ABNB", "DASH", "UBER", "LYFT", "NFLX",
    ],
    "Energy & Industrials": [
        "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HAL",
        "CAT", "DE", "UNP", "UPS", "FDX", "RTX", "LMT", "NOC", "GD", "BA",
        "HON", "GE", "MMM", "EMR", "ETN", "ITW", "ROK", "PH", "CARR", "OTIS",
    ],
}

ALL_STOCKS = []
for sector_stocks in STOCK_UNIVERSE.values():
    ALL_STOCKS.extend(sector_stocks)
ALL_STOCKS = list(set(ALL_STOCKS))  # Remove duplicates


def screen_stocks(
    sectors=None,
    min_market_cap=1_000_000_000,
    max_pe=None,
    min_pe=None,
    max_forward_pe=None,
    min_revenue_growth=None,
    min_dividend_yield=None,
    max_debt_to_equity=None,
    min_short_percent=None,
    near_52_week_low=False,
    near_52_week_high=False,
    min_volume_ratio=None,
    max_results=30,
    status_callback=None,
):
    """
    Screen stocks based on fundamental criteria.
    All data comes from Yahoo Finance - completely free.
    Returns a list of dicts with stock data that passed the filters.
    """
    # Determine which stocks to scan
    if sectors:
        tickers = []
        for sector in sectors:
            tickers.extend(STOCK_UNIVERSE.get(sector, []))
        tickers = list(set(tickers))
    else:
        tickers = ALL_STOCKS

    results = []
    total = len(tickers)

    for i, ticker in enumerate(tickers):
        if status_callback and i % 5 == 0:
            status_callback(f"Scanning {i}/{total}: {ticker}...")

        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            if not info or not info.get("currentPrice", info.get("regularMarketPrice")):
                continue

            price = info.get("currentPrice", info.get("regularMarketPrice", 0))
            market_cap = info.get("marketCap", 0) or 0
            pe = info.get("trailingPE")
            forward_pe = info.get("forwardPE")
            revenue = info.get("totalRevenue", 0) or 0
            revenue_growth = info.get("revenueGrowth")
            dividend_yield = info.get("dividendYield")
            debt_equity = info.get("debtToEquity")
            short_pct = info.get("shortPercentOfFloat")
            high_52w = info.get("fiftyTwoWeekHigh", 0) or 0
            low_52w = info.get("fiftyTwoWeekLow", 0) or 0
            avg_volume = info.get("averageVolume", 0) or 0
            current_volume = info.get("volume", 0) or 0
            target_price = info.get("targetMeanPrice")
            recommendation = info.get("recommendationKey", "")
            name = info.get("longName", info.get("shortName", ticker))
            sector = info.get("sector", "Unknown")

            # Apply filters
            if market_cap < min_market_cap:
                continue
            if max_pe is not None and (pe is None or pe > max_pe):
                continue
            if min_pe is not None and (pe is None or pe < min_pe):
                continue
            if max_forward_pe is not None and (forward_pe is None or forward_pe > max_forward_pe):
                continue
            if min_revenue_growth is not None and (revenue_growth is None or revenue_growth < min_revenue_growth / 100):
                continue
            if min_dividend_yield is not None and (dividend_yield is None or dividend_yield < min_dividend_yield / 100):
                continue
            if max_debt_to_equity is not None and (debt_equity is None or debt_equity > max_debt_to_equity):
                continue
            if min_short_percent is not None and (short_pct is None or short_pct * 100 < min_short_percent):
                continue
            if near_52_week_low and price > low_52w * 1.10:
                continue
            if near_52_week_high and price < high_52w * 0.95:
                continue
            if min_volume_ratio is not None and avg_volume > 0:
                vol_ratio = current_volume / avg_volume
                if vol_ratio < min_volume_ratio:
                    continue

            # Calculate upside to analyst target
            upside = None
            if target_price and price:
                upside = round((target_price - price) / price * 100, 1)

            # Position in 52-week range
            range_52w = None
            if high_52w and low_52w and high_52w != low_52w:
                range_52w = round((price - low_52w) / (high_52w - low_52w) * 100, 1)

            results.append({
                "ticker": ticker,
                "name": name,
                "sector": sector,
                "price": round(price, 2),
                "market_cap": market_cap,
                "market_cap_str": format_market_cap(market_cap),
                "pe_ratio": round(pe, 1) if pe else None,
                "forward_pe": round(forward_pe, 1) if forward_pe else None,
                "revenue_growth": round(revenue_growth * 100, 1) if revenue_growth else None,
                "dividend_yield": round(dividend_yield * 100, 2) if dividend_yield else None,
                "debt_to_equity": round(debt_equity, 1) if debt_equity else None,
                "short_percent": round(short_pct * 100, 1) if short_pct else None,
                "analyst_target": round(target_price, 2) if target_price else None,
                "upside_pct": upside,
                "recommendation": recommendation,
                "52w_range_pct": range_52w,
                "52w_high": round(high_52w, 2),
                "52w_low": round(low_52w, 2),
            })

        except Exception:
            continue

    # Sort by upside potential (most undervalued first)
    results.sort(key=lambda x: x.get("upside_pct") or -999, reverse=True)

    if status_callback:
        status_callback(f"Done! {len(results)} stocks passed your filters out of {total} scanned.")

    return results[:max_results]


def format_market_cap(cap):
    if cap >= 1_000_000_000_000:
        return f"${cap / 1_000_000_000_000:.1f}T"
    elif cap >= 1_000_000_000:
        return f"${cap / 1_000_000_000:.1f}B"
    elif cap >= 1_000_000:
        return f"${cap / 1_000_000:.0f}M"
    return f"${cap:,.0f}"


def get_available_sectors():
    return list(STOCK_UNIVERSE.keys())


def get_sector_stocks(sector):
    return STOCK_UNIVERSE.get(sector, [])
