import yfinance as yf
import requests
import time


# ── Hardcoded popular stocks beyond S&P 500 ──────────────────
EXTRA_STOCKS = [
    # Popular mid/small caps, meme stocks, growth names
    "HOOD", "SOFI", "PLTR", "RIVN", "LCID", "RBLX", "COIN", "MSTR", "AI",
    "SMCI", "ARM", "IONQ", "RGTI", "QUBT", "SOUN", "JOBY", "LUNR",
    "AFRM", "UPST", "HIMS", "DUOL", "CAVA", "BIRK", "GRAB",
    "SE", "MELI", "NU", "BABA", "JD", "PDD", "NIO", "LI", "XPEV",
    "SNAP", "PINS", "ROKU", "SPOT", "TTD", "MGNI", "PUBM",
    "NET", "DDOG", "ZS", "CRWD", "S", "OKTA", "MDB", "SNOW", "CFLT",
    "PATH", "DOCN", "GTLB", "BILL", "PCOR", "TOST", "TOAST",
    "CELH", "MNST", "SAM", "ELF", "ONON", "DECK", "CROX",
    "WOLF", "ENPH", "SEDG", "FSLR", "RUN", "NOVA",
    "CVNA", "W", "CHWY", "ETSY", "EBAY",
    "DKNG", "PENN", "RSI", "GENI", "FLUT",
    "MP", "LAC", "ALB", "LTHM", "SQM",
    "ARKG", "ARKK",  # Not stocks but people search for them
]


def get_sp500_tickers():
    """Return the full S&P 500 ticker list (hardcoded for reliability)."""
    return [
        "AAPL", "ABBV", "ABNB", "ABT", "ACGL", "ACN", "ADBE", "ADI", "ADP", "AEP", "AES", "AFL",
        "AJG", "ALGN", "ALL", "AMAT", "AMCR", "AMD", "AME", "AMGN", "AMP", "AMT", "AMZN", "ANET",
        "AON", "APD", "APH", "APO", "APP", "ARE", "ARES", "AVB", "AVGO", "AXON", "AXP", "AZO",
        "BA", "BAC", "BBY", "BEN", "BIIB", "BIO", "BK", "BKNG", "BKR", "BLK", "BMY", "BR",
        "BRK-B", "BRO", "BSX", "BWA", "BX", "C", "CAH", "CARR", "CAT", "CB", "CCI", "CCL",
        "CDAY", "CDNS", "CDW", "CEG", "CF", "CHD", "CHRW", "CI", "CL", "CLX", "CMCSA", "CME",
        "CMG", "CMI", "CNC", "COF", "COO", "COP", "COR", "COST", "CPB", "CPRT", "CPT", "CRH",
        "CRL", "CRM", "CRWD", "CSCO", "CSGP", "CSX", "CTAS", "CTRA", "CTSH", "CTVA", "CVS", "CVX",
        "D", "DAL", "DASH", "DAY", "DD", "DE", "DELL", "DFS", "DG", "DGX", "DHI", "DHR",
        "DIS", "DLR", "DLTR", "DOV", "DOW", "DPZ", "DRI", "DUK", "DVA", "DVN", "DXCM", "EA",
        "EBAY", "ECL", "EFX", "EG", "EL", "ELV", "EMR", "ENPH", "EOG", "EPAM", "EQIX", "EQR",
        "ES", "ESS", "ETN", "EW", "EXC", "EXPD", "EXR", "F", "FANG", "FAST", "FCX", "FDX",
        "FFIV", "FI", "FIS", "FITB", "FLT", "FOX", "FOXA", "FSLR", "FTNT", "FTV", "GD", "GE",
        "GEHC", "GEN", "GEV", "GILD", "GIS", "GLW", "GM", "GNRC", "GOOG", "GOOGL", "GPC", "GPN",
        "GRMN", "GS", "GWW", "HAL", "HBAN", "HCA", "HD", "HES", "HLT", "HOLX", "HON", "HOOD",
        "HPQ", "HRL", "HSIC", "HST", "HSY", "HUBB", "HUM", "HWM", "IBM", "ICE", "IDXX", "IFF",
        "INTC", "INTU", "INVH", "IP", "IPG", "IQV", "IR", "IRM", "ISRG", "ITW", "JBHT", "JCI",
        "JKHY", "JNJ", "JNPR", "JPM", "K", "KDP", "KEY", "KEYS", "KHC", "KKR", "KLAC", "KMB",
        "KMI", "KO", "KVUE", "LH", "LHX", "LIN", "LKQ", "LLY", "LMT", "LNG", "LNT", "LOW",
        "LRCX", "LULU", "LVS", "LW", "LYB", "LYV", "MA", "MAA", "MAR", "MCD", "MCHP", "MCK",
        "MCO", "MDLZ", "MDT", "MET", "META", "MKTX", "MLM", "MMM", "MNST", "MO", "MOH", "MOS",
        "MPC", "MPWR", "MRK", "MRNA", "MRO", "MRSH", "MRVL", "MS", "MSCI", "MSFT", "MSI", "MTB",
        "MTCH", "MTD", "MU", "NCLH", "NDAQ", "NEE", "NEM", "NFLX", "NI", "NKE", "NOC", "NOW",
        "NSC", "NTAP", "NTRS", "NUE", "NVDA", "NVR", "NWS", "NWSA", "NXPI", "O", "ODFL", "OKE",
        "ON", "ORCL", "ORLY", "OTIS", "PANW", "PAYC", "PAYX", "PCAR", "PCG", "PEAK", "PEG",
        "PEP", "PFE", "PG", "PGR", "PH", "PLD", "PLTR", "PM", "PNC", "PODD", "POOL", "PPG",
        "PSA", "PSX", "PWR", "PYPL", "QCOM", "QRVO", "RCL", "REGN", "RHI", "RJF", "RL", "RMD",
        "ROK", "ROL", "ROP", "ROST", "RSG", "RTX", "RVTY", "SBUX", "SCHW", "SHW", "SLB", "SNA",
        "SNDK", "SNPS", "SO", "SOLV", "SPG", "SPGI", "SRE", "STE", "STT", "STX", "STZ", "SWK",
        "SWKS", "SYK", "SYY", "T", "TDG", "TECH", "TEL", "TER", "TFC", "TFX", "TGT", "TJX",
        "TMO", "TMUS", "TRGP", "TRMB", "TROW", "TRV", "TSCO", "TSLA", "TSN", "TT", "TXN", "TXT",
        "TYL", "UBER", "ULTA", "UNH", "UNP", "UPS", "URI", "USB", "V", "VICI", "VLO", "VRTX",
        "VST", "VTR", "VTRS", "VZ", "WAB", "WAT", "WBA", "WBD", "WDC", "WEC", "WELL", "WFC",
        "WM", "WMB", "WMT", "WRB", "WST", "WY", "WYNN", "XEL", "XOM", "XYL", "YUM", "ZBH",
        "ZBRA", "ZTS",
    ]


def get_full_stock_list():
    """Get S&P 500 + popular extra stocks, deduplicated."""
    sp500 = get_sp500_tickers()
    all_tickers = list(set(sp500 + EXTRA_STOCKS))
    # Remove any ETFs or invalid entries
    all_tickers = [t for t in all_tickers if t and len(t) <= 5 and t.isalpha() or "-" in t]
    return sorted(all_tickers)


def scan_stock(ticker):
    """Fetch key data for a single stock. Returns dict or None on failure."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        if not info:
            return None

        price = info.get("currentPrice", info.get("regularMarketPrice"))
        if not price:
            return None

        market_cap = info.get("marketCap", 0) or 0
        if market_cap < 500_000_000:  # Skip micro-caps under $500M
            return None

        return {
            "ticker": ticker,
            "name": info.get("longName", info.get("shortName", ticker)),
            "sector": info.get("sector", "Unknown"),
            "industry": info.get("industry", "Unknown"),
            "price": round(price, 2),
            "market_cap": market_cap,
            "market_cap_str": format_market_cap(market_cap),
            "pe_ratio": safe_round(info.get("trailingPE")),
            "forward_pe": safe_round(info.get("forwardPE")),
            "revenue_growth": safe_round(info.get("revenueGrowth"), pct=True),
            "earnings_growth": safe_round(info.get("earningsGrowth"), pct=True),
            "profit_margin": safe_round(info.get("profitMargins"), pct=True),
            "dividend_yield": safe_round(info.get("dividendYield"), pct=True),
            "debt_to_equity": safe_round(info.get("debtToEquity")),
            "short_percent": safe_round(info.get("shortPercentOfFloat"), pct=True),
            "beta": safe_round(info.get("beta")),
            "analyst_target": safe_round(info.get("targetMeanPrice")),
            "recommendation": info.get("recommendationKey", ""),
            "num_analysts": info.get("numberOfAnalystOpinions", 0) or 0,
            "52w_high": info.get("fiftyTwoWeekHigh", 0) or 0,
            "52w_low": info.get("fiftyTwoWeekLow", 0) or 0,
            "avg_volume": info.get("averageVolume", 0) or 0,
            "current_volume": info.get("volume", 0) or 0,
        }
    except Exception:
        return None


def safe_round(val, decimals=1, pct=False):
    if val is None:
        return None
    try:
        if pct:
            return round(float(val) * 100, decimals)
        return round(float(val), decimals)
    except:
        return None


def format_market_cap(cap):
    if cap >= 1_000_000_000_000:
        return f"${cap / 1_000_000_000_000:.1f}T"
    elif cap >= 1_000_000_000:
        return f"${cap / 1_000_000_000:.1f}B"
    elif cap >= 1_000_000:
        return f"${cap / 1_000_000:.0f}M"
    return f"${cap:,.0f}"


def calculate_upside(stock):
    """Calculate upside to analyst target."""
    if stock.get("analyst_target") and stock.get("price"):
        return round((stock["analyst_target"] - stock["price"]) / stock["price"] * 100, 1)
    return None


def calculate_52w_position(stock):
    """Where is price in the 52-week range? 0% = at low, 100% = at high."""
    high = stock.get("52w_high", 0)
    low = stock.get("52w_low", 0)
    price = stock.get("price", 0)
    if high and low and high != low and price:
        return round((price - low) / (high - low) * 100, 1)
    return None


# ── The Four Strategies ──────────────────────────────────────

def filter_value_plays(stocks):
    """Low P/E, high analyst upside, profitable companies."""
    results = []
    for s in stocks:
        pe = s.get("pe_ratio")
        upside = calculate_upside(s)
        margin = s.get("profit_margin")
        analysts = s.get("num_analysts", 0)

        if (pe is not None and 0 < pe < 20
            and upside is not None and upside > 15
            and margin is not None and margin > 0
            and analysts >= 3):
            s["upside_pct"] = upside
            s["strategy"] = "VALUE"
            s["strategy_reason"] = f"P/E {pe}, {upside}% upside to target"
            results.append(s)

    results.sort(key=lambda x: x.get("upside_pct", 0), reverse=True)
    return results[:10]


def filter_growth_rockets(stocks):
    """High revenue growth, improving forward estimates."""
    results = []
    for s in stocks:
        rev_growth = s.get("revenue_growth")
        forward_pe = s.get("forward_pe")
        pe = s.get("pe_ratio")
        upside = calculate_upside(s)

        if (rev_growth is not None and rev_growth > 20
            and forward_pe is not None
            and (pe is None or forward_pe < pe)):  # Forward P/E improving
            s["upside_pct"] = upside
            s["strategy"] = "GROWTH"
            pe_improving = f", P/E improving {pe}->{forward_pe}" if pe else ""
            s["strategy_reason"] = f"Revenue +{rev_growth}%{pe_improving}"
            results.append(s)

    results.sort(key=lambda x: x.get("revenue_growth", 0), reverse=True)
    return results[:10]


def filter_insider_signals(stocks):
    """Stocks with recent insider buying (checked via Yahoo Finance)."""
    results = []
    for s in stocks:
        ticker = s["ticker"]
        try:
            stock = yf.Ticker(ticker)
            insiders = stock.insider_transactions
            if insiders is None or insiders.empty:
                continue

            # Look for buys
            total_buy_value = 0
            buy_count = 0
            for _, row in insiders.head(10).iterrows():
                trade_type = str(row.get("Transaction", row.get("Text", ""))).lower()
                value = row.get("Value", 0) or 0
                if ("buy" in trade_type or "purchase" in trade_type) and value > 0:
                    total_buy_value += value
                    buy_count += 1

            if total_buy_value >= 50_000:
                upside = calculate_upside(s)
                s["upside_pct"] = upside
                s["strategy"] = "INSIDER"
                s["insider_buy_value"] = total_buy_value
                s["strategy_reason"] = f"{buy_count} insider buys totaling ${total_buy_value:,.0f}"
                results.append(s)

        except Exception:
            continue

    results.sort(key=lambda x: x.get("insider_buy_value", 0), reverse=True)
    return results[:10]


def filter_bounce_candidates(stocks):
    """Near 52-week lows but still fundamentally sound."""
    results = []
    for s in stocks:
        position = calculate_52w_position(s)
        margin = s.get("profit_margin")
        rec = s.get("recommendation", "")
        analysts = s.get("num_analysts", 0)
        upside = calculate_upside(s)

        # Within 15% of 52-week low
        if (position is not None and position < 15
            and (
                (margin is not None and margin > 0)  # Still profitable
                or (rec in ["buy", "strong_buy"] and analysts >= 3)  # Or analysts say buy
            )):
            s["upside_pct"] = upside
            s["52w_position"] = position
            s["strategy"] = "BOUNCE"
            s["strategy_reason"] = f"Only {position}% above 52w low, {upside}% upside" if upside else f"Only {position}% above 52w low"
            results.append(s)

    results.sort(key=lambda x: x.get("52w_position", 100))
    return results[:10]


# ── Main Screener Function ───────────────────────────────────

def run_full_screener(
    strategies=None,
    max_candidates=30,
    status_callback=None,
):
    """
    Full market screener with 4-strategy funnel.

    Stage 1: Scan all stocks (free)
    Stage 2: Apply strategy filters
    Stage 3: Deduplicate and rank

    Returns list of candidate stocks ready for Claude analysis.
    """
    if strategies is None:
        strategies = ["VALUE", "GROWTH", "INSIDER", "BOUNCE"]

    # Step 1: Get ticker list
    if status_callback:
        status_callback("Loading stock universe...")

    tickers = get_full_stock_list()
    total = len(tickers)

    if status_callback:
        status_callback(f"Scanning {total} stocks...")

    # Step 2: Scan all stocks for basic data
    all_stocks = []
    for i, ticker in enumerate(tickers):
        if status_callback and i % 10 == 0:
            pct = round(i / total * 100)
            status_callback(f"Scanning {i}/{total} ({pct}%): {ticker}...")

        data = scan_stock(ticker)
        if data:
            all_stocks.append(data)

        # Small delay every 20 stocks to avoid rate limiting
        if i % 20 == 0 and i > 0:
            time.sleep(0.5)

    if status_callback:
        status_callback(f"Scanned {total} tickers, {len(all_stocks)} valid stocks found. Running strategy filters...")

    # Step 3: Run strategy filters
    all_candidates = []

    if "VALUE" in strategies:
        if status_callback:
            status_callback("Running VALUE filter (low P/E + high upside)...")
        value = filter_value_plays(all_stocks)
        all_candidates.extend(value)
        if status_callback:
            status_callback(f"  Found {len(value)} value plays")

    if "GROWTH" in strategies:
        if status_callback:
            status_callback("Running GROWTH filter (high revenue growth)...")
        growth = filter_growth_rockets(all_stocks)
        all_candidates.extend(growth)
        if status_callback:
            status_callback(f"  Found {len(growth)} growth rockets")

    if "INSIDER" in strategies:
        if status_callback:
            status_callback("Running INSIDER filter (checking insider transactions, this takes a few minutes)...")
        # Only check insider data for stocks that look decent
        decent_stocks = [s for s in all_stocks if s.get("num_analysts", 0) >= 2]
        insider = filter_insider_signals(decent_stocks[:100])  # Limit to top 100 to save time
        all_candidates.extend(insider)
        if status_callback:
            status_callback(f"  Found {len(insider)} insider signals")

    if "BOUNCE" in strategies:
        if status_callback:
            status_callback("Running BOUNCE filter (near 52-week lows)...")
        bounce = filter_bounce_candidates(all_stocks)
        all_candidates.extend(bounce)
        if status_callback:
            status_callback(f"  Found {len(bounce)} bounce candidates")

    # Step 4: Deduplicate (stock might appear in multiple strategies)
    seen = {}
    for s in all_candidates:
        ticker = s["ticker"]
        if ticker in seen:
            # Stock appeared in multiple strategies - boost it
            seen[ticker]["strategies"] = seen[ticker].get("strategies", [seen[ticker]["strategy"]])
            if s["strategy"] not in seen[ticker]["strategies"]:
                seen[ticker]["strategies"].append(s["strategy"])
                seen[ticker]["strategy_reason"] += f" | {s['strategy_reason']}"
                seen[ticker]["multi_strategy"] = True
        else:
            s["strategies"] = [s["strategy"]]
            s["multi_strategy"] = False
            seen[ticker] = s

    # Step 5: Sort - multi-strategy stocks first, then by upside
    final = list(seen.values())
    final.sort(key=lambda x: (
        -len(x.get("strategies", [])),  # More strategies = better
        -(x.get("upside_pct") or -999),  # Higher upside = better
    ))

    if status_callback:
        multi = sum(1 for s in final if s.get("multi_strategy"))
        status_callback(
            f"Done! {len(final)} unique candidates found. "
            f"{multi} appeared in multiple strategies (strongest signals)."
        )

    return final[:max_candidates]


def get_available_sectors():
    """Return list of sectors for UI."""
    return ["Technology", "Healthcare", "Financial", "Consumer", "Energy & Industrials"]


# ── Simple screener (original, for quick scans) ─────────────

def screen_stocks_simple(
    sectors=None,
    min_market_cap=1_000_000_000,
    max_pe=None,
    min_revenue_growth=None,
    max_debt_to_equity=None,
    near_52_week_low=False,
    near_52_week_high=False,
    max_results=30,
    status_callback=None,
):
    """Quick scan of ~170 popular stocks with custom filters."""
    STOCK_UNIVERSE = {
        "Technology": [
            "AAPL", "MSFT", "GOOGL", "META", "NVDA", "TSLA", "AVGO", "ADBE", "CRM", "AMD",
            "INTC", "ORCL", "CSCO", "QCOM", "TXN", "NOW", "IBM", "AMAT", "MU", "LRCX",
            "KLAC", "SNPS", "CDNS", "MRVL", "FTNT", "PANW", "CRWD", "ZS", "DDOG", "NET",
            "SNOW", "PLTR", "SHOP", "SQ", "COIN", "HOOD", "RBLX", "TWLO",
        ],
        "Healthcare": [
            "UNH", "JNJ", "LLY", "PFE", "ABBV", "MRK", "TMO", "ABT", "DHR", "BMY",
            "AMGN", "GILD", "ISRG", "CVS", "ELV", "CI", "SYK", "BSX", "VRTX", "REGN",
        ],
        "Financial": [
            "BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "SCHW", "BLK",
            "C", "AXP", "SPGI", "CME", "ICE", "PGR", "CB", "PYPL", "SOFI",
        ],
        "Consumer": [
            "AMZN", "HD", "MCD", "NKE", "SBUX", "TGT", "COST", "WMT", "LOW", "TJX",
            "BKNG", "MAR", "HLT", "CMG", "YUM", "LULU", "DG", "NFLX", "DIS", "ABNB",
            "UBER", "DASH",
        ],
        "Energy & Industrials": [
            "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "OXY",
            "CAT", "DE", "UNP", "UPS", "RTX", "LMT", "NOC", "BA",
            "HON", "GE", "ETN", "PH",
        ],
    }

    if sectors:
        tickers = []
        for sector in sectors:
            tickers.extend(STOCK_UNIVERSE.get(sector, []))
        tickers = list(set(tickers))
    else:
        tickers = []
        for stocks in STOCK_UNIVERSE.values():
            tickers.extend(stocks)
        tickers = list(set(tickers))

    results = []
    total = len(tickers)

    for i, ticker in enumerate(tickers):
        if status_callback and i % 5 == 0:
            status_callback(f"Scanning {i}/{total}: {ticker}...")

        data = scan_stock(ticker)
        if not data:
            continue

        # Apply filters
        if data["market_cap"] < min_market_cap:
            continue
        if max_pe and (data["pe_ratio"] is None or data["pe_ratio"] > max_pe):
            continue
        if min_revenue_growth and (data["revenue_growth"] is None or data["revenue_growth"] < min_revenue_growth):
            continue
        if max_debt_to_equity and (data["debt_to_equity"] is None or data["debt_to_equity"] > max_debt_to_equity):
            continue

        position = calculate_52w_position(data)
        if near_52_week_low and (position is None or position > 15):
            continue
        if near_52_week_high and (position is None or position < 85):
            continue

        data["upside_pct"] = calculate_upside(data)
        data["52w_position"] = position
        results.append(data)

    results.sort(key=lambda x: x.get("upside_pct") or -999, reverse=True)

    if status_callback:
        status_callback(f"Done! {len(results)} stocks passed filters.")

    return results[:max_results]
