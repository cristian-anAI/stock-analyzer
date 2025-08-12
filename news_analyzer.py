import requests
import datetime
import time
from typing import Optional
try:
    from textblob import TextBlob
except ImportError:
    TextBlob = None

class NewsAnalyzer:
    def __init__(self):
        self.cache = {}  # {symbol: (timestamp, sentiment)}
        self.cache_ttl = 3600  # 1 hora

    def get_news_sentiment(self, symbol: str) -> Optional[float]:
        now = time.time()
        # Cache
        if symbol in self.cache:
            ts, sentiment = self.cache[symbol]
            if now - ts < self.cache_ttl:
                return sentiment
        try:
            news = self._fetch_yahoo_news(symbol)
            if not news:
                return 0  # Neutral fallback
            text = ' '.join([n['title'] + ' ' + n.get('summary', '') for n in news])
            sentiment = self._analyze_sentiment(text)
            self.cache[symbol] = (now, sentiment)
            return sentiment
        except Exception:
            return 0  # Fallback neutral

    def _fetch_yahoo_news(self, symbol: str):
        url = f"https://finance.yahoo.com/quote/{symbol}/news?p={symbol}"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return []
        # Simple scraping: busca títulos de noticias
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        articles = []
        for item in soup.find_all('li', attrs={'class': 'js-stream-content'}):
            title_tag = item.find('h3')
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            summary_tag = item.find('p')
            summary = summary_tag.get_text(strip=True) if summary_tag else ''
            articles.append({'title': title, 'summary': summary})
        return articles

    def _analyze_sentiment(self, text: str) -> float:
        if TextBlob is not None:
            blob = TextBlob(text)
            return max(-1, min(1, blob.sentiment.polarity))
        # Fallback neutral
        return 0
