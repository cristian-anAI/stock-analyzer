from news_analyzer import NewsAnalyzer

if __name__ == "__main__":
    analyzer = NewsAnalyzer()
    symbol = "DFEN"
    sentiment = analyzer.get_news_sentiment(symbol)
    print(f"Sentimiento de noticias para {symbol}: {sentiment}")
