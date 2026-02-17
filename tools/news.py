import requests
from models import NewsItem
try:
    from config import NEWS_API_KEY
except:
    NEWS_API_KEY = ""


def get_stock_news(
    ticker: str, company_name: str, max_articles: int = 10
) -> list[NewsItem]:
    if not NEWS_API_KEY:
        return [
            NewsItem(
                title="[News unavailable - no NEWS_API_KEY set]",
                source="system",
                published_at="",
                summary="Set NEWS_API_KEY in config.py to enable news. "
                "Get a free key at https://newsapi.org",
            )
        ]

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": f'"{company_name}" OR "{ticker}"',
        "sortBy": "publishedAt",
        "pageSize": max_articles,
        "language": "en",
        "apiKey": NEWS_API_KEY,
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        return [
            NewsItem(
                title=f"[News fetch error: {e}]",
                source="system",
                published_at="",
                summary="",
            )
        ]

    articles = resp.json().get("articles", [])
    return [
        NewsItem(
            title=a["title"],
            source=a["source"]["name"],
            published_at=a["publishedAt"],
            summary=a.get("description", "") or "",
        )
        for a in articles
        if a.get("title") and a["title"] != "[Removed]"
    ]
