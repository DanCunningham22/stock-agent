import anthropic
import json

from config import ANTHROPIC_API_KEY, MODEL_FAST, MAX_TOKENS_PER_STOCK
from tools.market_data import (
    get_stock_data, get_financial_statements, get_price_history,
    get_insider_trades, get_analyst_estimates, get_macro_data,
    get_sector_performance,
)
from tools.polymarket import get_polymarket_for_stock
from tools.news import get_stock_news
from tools.cache import get_cached, set_cached
from tools.alerts import check_alerts, send_alerts
from prompts.system import ANALYSIS_SYSTEM_PROMPT

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

TOOLS = [
    {
        "name": "get_stock_data",
        "description": "Fetch current stock price, market cap, P/E, revenue, earnings, debt/equity, short interest, analyst targets, and other key metrics.",
        "input_schema": {
            "type": "object",
            "properties": {"ticker": {"type": "string", "description": "Stock ticker (e.g. 'AAPL')"}},
            "required": ["ticker"],
        },
    },
    {
        "name": "get_financial_statements",
        "description": "Fetch income statement, balance sheet, cash flow (last 4 years).",
        "input_schema": {
            "type": "object",
            "properties": {"ticker": {"type": "string"}},
            "required": ["ticker"],
        },
    },
    {
        "name": "get_price_history",
        "description": "Fetch price history with moving averages (50d, 200d), volume analysis, and returns (1d/1w/1m/3m).",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "period": {"type": "string", "default": "1y"},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_insider_trades",
        "description": "Fetch recent insider buys/sells by executives and directors.",
        "input_schema": {
            "type": "object",
            "properties": {"ticker": {"type": "string"}},
            "required": ["ticker"],
        },
    },
    {
        "name": "get_analyst_estimates",
        "description": "Fetch analyst price targets, consensus rating, earnings/revenue estimates.",
        "input_schema": {
            "type": "object",
            "properties": {"ticker": {"type": "string"}},
            "required": ["ticker"],
        },
    },
    {
        "name": "get_macro_data",
        "description": "Fetch macro indicators: S&P 500, VIX (fear index), 10-year Treasury yield.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_sector_performance",
        "description": "Fetch 1-month performance of all major sector ETFs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sector_etf": {"type": "string", "description": "Optional specific ETF ticker"},
            },
        },
    },
    {
        "name": "get_polymarket_data",
        "description": (
            "Fetch prediction market data from Polymarket. Returns current betting odds "
            "on macro events (Fed rates, recession, tariffs, etc.) and any company-specific "
            "markets. These represent real money bets on future outcomes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker"},
                "company_name": {"type": "string", "description": "Full company name"},
            },
            "required": ["ticker", "company_name"],
        },
    },
    {
        "name": "get_stock_news",
        "description": "Fetch recent news articles for sentiment analysis.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "company_name": {"type": "string"},
                "max_articles": {"type": "integer", "default": 10},
            },
            "required": ["ticker", "company_name"],
        },
    },
]


def execute_tool(name: str, input_data: dict) -> str:
    try:
        if name == "get_stock_data":
            cache_key = f"stock_data:{input_data['ticker']}"
            cached = get_cached(cache_key)
            if cached:
                return json.dumps(cached, default=str)
            result = get_stock_data(input_data["ticker"])
            result_dict = result.model_dump()
            set_cached(cache_key, result_dict, ttl_days=1)
            return json.dumps(result_dict, default=str)

        elif name == "get_financial_statements":
            cache_key = f"financials:{input_data['ticker']}"
            cached = get_cached(cache_key)
            if cached:
                return json.dumps(cached, default=str)
            result = get_financial_statements(input_data["ticker"])
            set_cached(cache_key, result, ttl_days=7)
            return json.dumps(result, default=str)

        elif name == "get_price_history":
            result = get_price_history(input_data["ticker"], input_data.get("period", "1y"))
            return json.dumps(result, default=str)

        elif name == "get_insider_trades":
            return json.dumps(get_insider_trades(input_data["ticker"]), default=str)

        elif name == "get_analyst_estimates":
            cache_key = f"estimates:{input_data['ticker']}"
            cached = get_cached(cache_key)
            if cached:
                return json.dumps(cached, default=str)
            result = get_analyst_estimates(input_data["ticker"])
            set_cached(cache_key, result, ttl_days=1)
            return json.dumps(result, default=str)

        elif name == "get_macro_data":
            cache_key = "macro_data"
            cached = get_cached(cache_key)
            if cached:
                return json.dumps(cached, default=str)
            result = get_macro_data()
            set_cached(cache_key, result, ttl_days=1)
            return json.dumps(result, default=str)

        elif name == "get_sector_performance":
            cache_key = "sector_perf"
            cached = get_cached(cache_key)
            if cached:
                return json.dumps(cached, default=str)
            result = get_sector_performance(input_data.get("sector_etf"))
            set_cached(cache_key, result, ttl_days=1)
            return json.dumps(result, default=str)

        elif name == "get_polymarket_data":
            cache_key = f"polymarket:{input_data['ticker']}"
            cached = get_cached(cache_key)
            if cached:
                return json.dumps(cached, default=str)
            result = get_polymarket_for_stock(input_data["ticker"], input_data["company_name"])
            set_cached(cache_key, result, ttl_days=1)
            return json.dumps(result, default=str)

        elif name == "get_stock_news":
            result = get_stock_news(
                input_data["ticker"], input_data["company_name"],
                input_data.get("max_articles", 10),
            )
            return json.dumps([item.model_dump() for item in result], default=str)

        else:
            return json.dumps({"error": f"Unknown tool: {name}"})

    except Exception as e:
        return json.dumps({"error": f"{type(e).__name__}: {e}"})


def analyze_stock(ticker: str, status_callback=None, run_alerts=True) -> str:
    def update_status(msg):
        if status_callback:
            status_callback(msg)
        print(f"  {msg}")

    messages = [
        {
            "role": "user",
            "content": (
                f"Research and analyze {ticker}. Follow this workflow:\n\n"
                f"1. Fetch current stock data for {ticker}.\n"
                f"2. Fetch financial statements.\n"
                f"3. Get 1-year price history with moving averages.\n"
                f"4. Fetch insider transactions.\n"
                f"5. Fetch analyst estimates and price targets.\n"
                f"6. Fetch macro data (S&P 500, VIX, yields).\n"
                f"7. Fetch sector performance.\n"
                f"8. Fetch Polymarket prediction market data.\n"
                f"9. Fetch recent news.\n"
                f"10. Produce comprehensive analysis with scoring.\n\n"
                f"Be quantitative. Include the full scorecard. Include Polymarket signals."
            ),
        }
    ]

    total_input_tokens = 0
    total_output_tokens = 0
    collected_stock_data = {}
    collected_price_data = {}
    collected_insider_data = []

    while (total_input_tokens + total_output_tokens) < MAX_TOKENS_PER_STOCK:
        response = client.messages.create(
            model=MODEL_FAST,
            max_tokens=6000,
            system=ANALYSIS_SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        total_input_tokens += response.usage.input_tokens
        total_output_tokens += response.usage.output_tokens

        tool_results = []
        final_text = ""

        for block in response.content:
            if block.type == "text":
                final_text += block.text
            elif block.type == "tool_use":
                update_status(f"Calling {block.name}...")
                tool_output = execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": tool_output,
                })
                try:
                    parsed = json.loads(tool_output)
                    if block.name == "get_stock_data":
                        collected_stock_data = parsed
                    elif block.name == "get_price_history":
                        collected_price_data = parsed
                    elif block.name == "get_insider_trades":
                        collected_insider_data = parsed
                except:
                    pass

        if response.stop_reason == "end_turn":
            tokens_used = total_input_tokens + total_output_tokens
            update_status(f"Done! {tokens_used:,} total tokens")

            if run_alerts and collected_stock_data and collected_price_data:
                update_status("Checking alerts...")
                alerts = check_alerts(ticker, collected_stock_data, collected_price_data, collected_insider_data)
                if alerts:
                    update_status(f"{len(alerts)} alerts triggered!")
                    send_alerts(alerts)
                else:
                    update_status("No alerts triggered")

            return final_text

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    return f"WARNING: Token budget exceeded for {ticker}"


def run_daily_research(watchlist, status_callback=None):
    reports = {}
    for i, ticker in enumerate(watchlist, 1):
        if status_callback:
            status_callback(f"[{i}/{len(watchlist)}] Analyzing {ticker}...")
        else:
            print(f"\n[{i}/{len(watchlist)}] Analyzing {ticker}...")
        try:
            report = analyze_stock(ticker, status_callback)
            reports[ticker] = report
        except Exception as e:
            reports[ticker] = f"# {ticker}\n\nError: {e}"
    return reports


def run_alert_scan(watchlist, status_callback=None):
    all_alerts = []
    for ticker in watchlist:
        if status_callback:
            status_callback(f"Scanning {ticker}...")
        else:
            print(f"Scanning {ticker}...")
        try:
            stock_data = get_stock_data(ticker).model_dump()
            price_data = get_price_history(ticker, "1y")
            insider_data = get_insider_trades(ticker)
            alerts = check_alerts(ticker, stock_data, price_data, insider_data)
            all_alerts.extend(alerts)
        except Exception as e:
            print(f"  Error scanning {ticker}: {e}")
    if all_alerts:
        send_alerts(all_alerts)
    return all_alerts
