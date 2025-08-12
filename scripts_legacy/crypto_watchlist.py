# crypto_watchlist.py
"""
Defines the top 20 cryptocurrencies for analysis, with stable/volatile classification and market cap filtering.
"""

CRYPTO_WATCHLIST = [
    {"symbol": "BTC-USD", "name": "Bitcoin", "type": "stable"},
    {"symbol": "ETH-USD", "name": "Ethereum", "type": "stable"},
    {"symbol": "SOL-USD", "name": "Solana", "type": "volatile"},
    {"symbol": "ADA-USD", "name": "Cardano", "type": "volatile"},
    {"symbol": "DOT-USD", "name": "Polkadot", "type": "volatile"},
    {"symbol": "LINK-USD", "name": "Chainlink", "type": "volatile"},
    {"symbol": "AVAX-USD", "name": "Avalanche", "type": "volatile"},
    {"symbol": "MATIC-USD", "name": "Polygon", "type": "volatile"},
    {"symbol": "DOGE-USD", "name": "Dogecoin", "type": "volatile"},
    {"symbol": "TRX-USD", "name": "Tron", "type": "volatile"},
    {"symbol": "LTC-USD", "name": "Litecoin", "type": "volatile"},
    {"symbol": "BCH-USD", "name": "Bitcoin Cash", "type": "volatile"},
    {"symbol": "XLM-USD", "name": "Stellar", "type": "volatile"},
    {"symbol": "ATOM-USD", "name": "Cosmos", "type": "volatile"},
    {"symbol": "UNI-USD", "name": "Uniswap", "type": "volatile"},
    {"symbol": "AAVE-USD", "name": "Aave", "type": "volatile"},
    {"symbol": "FIL-USD", "name": "Filecoin", "type": "volatile"},
    {"symbol": "HBAR-USD", "name": "Hedera", "type": "volatile"},
    {"symbol": "VET-USD", "name": "VeChain", "type": "volatile"},
    {"symbol": "ICP-USD", "name": "Internet Computer", "type": "volatile"},
]

# Market cap filtering (CoinGecko API example)
def filter_by_market_cap(coin_list, min_market_cap_usd=1_000_000_000):
    """Filter cryptos by market cap using CoinGecko API."""
    import requests
    filtered = []
    for coin in coin_list:
        coingecko_id = coin["name"].lower().replace(" ", "-")
        url = f"https://api.coingecko.com/api/v3/coins/{coingecko_id}"
        resp = requests.get(url)
        if resp.status_code == 200:
            data = resp.json()
            market_cap = data.get("market_data", {}).get("market_cap", {}).get("usd", 0)
            if market_cap >= min_market_cap_usd:
                filtered.append(coin)
    return filtered
