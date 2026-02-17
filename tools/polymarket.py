import requests

GAMMA_API = "https://gamma-api.polymarket.com"

# Keywords to search for markets relevant to stock investing
MARKET_KEYWORDS = [
    "fed", "interest rate", "recession", "inflation", "s&p",
    "stock market", "gdp", "unemployment", "tariff", "trade war",
    "bitcoin", "crypto", "oil price", "treasury",
]


def get_polymarket_data(search_query: str = None) -> dict:
    """
    Fetch relevant prediction markets from Polymarket's Gamma API.
    If no query given, fetches markets relevant to stock investing.
    Returns top markets with their current probability/prices.
    """
    results = []

    queries = [search_query] if search_query else MARKET_KEYWORDS

    seen_ids = set()

    for query in queries:
        try:
            resp = requests.get(
                f"{GAMMA_API}/events",
                params={
                    "closed": "false",
                    "limit": 5,
                    "order": "volume",
                    "ascending": "false",
                    "title": query,
                },
                timeout=10,
            )
            if resp.status_code != 200:
                continue

            events = resp.json()
            if not isinstance(events, list):
                continue

            for event in events:
                event_id = event.get("id")
                if event_id in seen_ids:
                    continue
                seen_ids.add(event_id)

                title = event.get("title", "")
                markets = event.get("markets", [])

                for market in markets:
                    outcome_prices = market.get("outcomePrices", "")
                    outcomes = market.get("outcomes", "")

                    # Parse outcome prices
                    try:
                        if isinstance(outcome_prices, str):
                            # Format: "[\"0.85\",\"0.15\"]"
                            import json
                            prices = json.loads(outcome_prices)
                        elif isinstance(outcome_prices, list):
                            prices = outcome_prices
                        else:
                            prices = []
                    except:
                        prices = []

                    try:
                        if isinstance(outcomes, str):
                            import json
                            outcome_names = json.loads(outcomes)
                        elif isinstance(outcomes, list):
                            outcome_names = outcomes
                        else:
                            outcome_names = []
                    except:
                        outcome_names = []

                    # Build readable probability
                    probabilities = {}
                    for i, name in enumerate(outcome_names):
                        if i < len(prices):
                            try:
                                prob = float(prices[i]) * 100
                                probabilities[name] = f"{prob:.0f}%"
                            except:
                                pass

                    volume = market.get("volume", 0)
                    try:
                        volume = float(volume)
                    except:
                        volume = 0

                    if probabilities and volume > 10000:  # Only include active markets
                        results.append({
                            "question": market.get("question", title),
                            "probabilities": probabilities,
                            "volume": f"${volume:,.0f}",
                            "category": query,
                        })

        except Exception as e:
            continue

    # Sort by volume (most active first) and deduplicate
    # Take top 15 most relevant markets
    results = results[:15]

    if not results:
        return {
            "status": "No relevant prediction markets found",
            "markets": [],
        }

    return {
        "status": f"Found {len(results)} relevant prediction markets",
        "markets": results,
    }


def get_polymarket_for_stock(ticker: str, company_name: str) -> dict:
    """
    Search Polymarket for any markets directly related to a specific stock or company.
    Also fetches general macro markets that would affect any stock.
    """
    # Search for company-specific markets
    company_markets = get_polymarket_data(company_name)

    # Also get ticker-specific
    ticker_markets = get_polymarket_data(ticker)

    # Get general macro markets
    macro_markets = get_polymarket_data(None)

    # Combine and deduplicate
    all_markets = []
    seen_questions = set()

    for source in [company_markets, ticker_markets, macro_markets]:
        for market in source.get("markets", []):
            q = market.get("question", "")
            if q not in seen_questions:
                seen_questions.add(q)
                all_markets.append(market)

    # Separate into company-specific and macro
    company_specific = []
    macro = []

    for m in all_markets:
        q = m.get("question", "").lower()
        if ticker.lower() in q or company_name.lower() in q:
            company_specific.append(m)
        else:
            macro.append(m)

    return {
        "company_specific_markets": company_specific[:5],
        "macro_markets": macro[:10],
        "total_markets_found": len(all_markets),
    }
