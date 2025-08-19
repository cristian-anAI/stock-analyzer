#!/usr/bin/env python3
"""
EXPANDED CRYPTO WATCHLIST - Top 50 Cryptos by Market Cap
Organized by tier and use case for better diversification
"""

# TOP 50 CRYPTOS BY MARKET CAP (Updated August 2025)
EXPANDED_CRYPTO_WATCHLIST = [
    # TIER 1: Blue-chip cryptos (Top 10 by market cap)
    {"symbol": "BTC-USD", "name": "Bitcoin", "tier": "blue_chip", "type": "store_of_value", "market_cap_rank": 1},
    {"symbol": "ETH-USD", "name": "Ethereum", "tier": "blue_chip", "type": "smart_platform", "market_cap_rank": 2},
    {"symbol": "USDT-USD", "name": "Tether", "tier": "stablecoin", "type": "stablecoin", "market_cap_rank": 3},
    {"symbol": "BNB-USD", "name": "BNB", "tier": "blue_chip", "type": "exchange_token", "market_cap_rank": 4},
    {"symbol": "SOL-USD", "name": "Solana", "tier": "blue_chip", "type": "smart_platform", "market_cap_rank": 5},
    {"symbol": "USDC-USD", "name": "USD Coin", "tier": "stablecoin", "type": "stablecoin", "market_cap_rank": 6},
    {"symbol": "XRP-USD", "name": "XRP", "tier": "blue_chip", "type": "payment", "market_cap_rank": 7},
    {"symbol": "DOGE-USD", "name": "Dogecoin", "tier": "blue_chip", "type": "meme", "market_cap_rank": 8},
    {"symbol": "TRX-USD", "name": "TRON", "tier": "blue_chip", "type": "smart_platform", "market_cap_rank": 9},
    {"symbol": "TON11419-USD", "name": "Toncoin", "tier": "blue_chip", "type": "smart_platform", "market_cap_rank": 10},
    
    # TIER 2: Major altcoins (11-25)
    {"symbol": "ADA-USD", "name": "Cardano", "tier": "major_alt", "type": "smart_platform", "market_cap_rank": 11},
    {"symbol": "AVAX-USD", "name": "Avalanche", "tier": "major_alt", "type": "smart_platform", "market_cap_rank": 12},
    {"symbol": "SHIB-USD", "name": "Shiba Inu", "tier": "major_alt", "type": "meme", "market_cap_rank": 13},
    {"symbol": "LINK-USD", "name": "Chainlink", "tier": "major_alt", "type": "oracle", "market_cap_rank": 14},
    {"symbol": "BCH-USD", "name": "Bitcoin Cash", "tier": "major_alt", "type": "payment", "market_cap_rank": 15},
    {"symbol": "DOT-USD", "name": "Polkadot", "tier": "major_alt", "type": "interoperability", "market_cap_rank": 16},
    {"symbol": "NEAR-USD", "name": "NEAR Protocol", "tier": "major_alt", "type": "smart_platform", "market_cap_rank": 17},
    {"symbol": "MATIC-USD", "name": "Polygon", "tier": "major_alt", "type": "scaling", "market_cap_rank": 18},
    {"symbol": "LTC-USD", "name": "Litecoin", "tier": "major_alt", "type": "payment", "market_cap_rank": 19},
    {"symbol": "UNI7083-USD", "name": "Uniswap", "tier": "major_alt", "type": "defi", "market_cap_rank": 20},
    {"symbol": "ICP-USD", "name": "Internet Computer", "tier": "major_alt", "type": "web3", "market_cap_rank": 21},
    {"symbol": "ETC-USD", "name": "Ethereum Classic", "tier": "major_alt", "type": "smart_platform", "market_cap_rank": 22},
    {"symbol": "HBAR-USD", "name": "Hedera", "tier": "major_alt", "type": "enterprise", "market_cap_rank": 23},
    {"symbol": "APT21794-USD", "name": "Aptos", "tier": "major_alt", "type": "smart_platform", "market_cap_rank": 24},
    {"symbol": "STX4847-USD", "name": "Stacks", "tier": "major_alt", "type": "bitcoin_layer2", "market_cap_rank": 25},
    
    # TIER 3: Growth altcoins (26-40)
    {"symbol": "ATOM-USD", "name": "Cosmos", "tier": "growth", "type": "interoperability", "market_cap_rank": 26},
    {"symbol": "VET-USD", "name": "VeChain", "tier": "growth", "type": "supply_chain", "market_cap_rank": 27},
    {"symbol": "FIL-USD", "name": "Filecoin", "tier": "growth", "type": "storage", "market_cap_rank": 28},
    {"symbol": "AAVE-USD", "name": "Aave", "tier": "growth", "type": "defi", "market_cap_rank": 29},
    {"symbol": "OP-USD", "name": "Optimism", "tier": "growth", "type": "scaling", "market_cap_rank": 30},
    {"symbol": "ARB11841-USD", "name": "Arbitrum", "tier": "growth", "type": "scaling", "market_cap_rank": 31},
    {"symbol": "MKR-USD", "name": "Maker", "tier": "growth", "type": "defi", "market_cap_rank": 32},
    {"symbol": "GRT6719-USD", "name": "The Graph", "tier": "growth", "type": "indexing", "market_cap_rank": 33},
    {"symbol": "LDO-USD", "name": "Lido DAO", "tier": "growth", "type": "defi_staking", "market_cap_rank": 34},
    {"symbol": "CRV-USD", "name": "Curve DAO", "tier": "growth", "type": "defi", "market_cap_rank": 35},
    {"symbol": "QNT-USD", "name": "Quant", "tier": "growth", "type": "interoperability", "market_cap_rank": 36},
    {"symbol": "MANA-USD", "name": "Decentraland", "tier": "growth", "type": "metaverse", "market_cap_rank": 37},
    {"symbol": "SAND-USD", "name": "The Sandbox", "tier": "growth", "type": "metaverse", "market_cap_rank": 38},
    {"symbol": "XLM-USD", "name": "Stellar", "tier": "growth", "type": "payment", "market_cap_rank": 39},
    {"symbol": "ALGO-USD", "name": "Algorand", "tier": "growth", "type": "smart_platform", "market_cap_rank": 40},
    
    # TIER 4: Emerging opportunities (41-50)
    {"symbol": "FLOW-USD", "name": "Flow", "tier": "emerging", "type": "nft_gaming", "market_cap_rank": 41},
    {"symbol": "XTZ-USD", "name": "Tezos", "tier": "emerging", "type": "smart_platform", "market_cap_rank": 42},
    {"symbol": "EGLD-USD", "name": "MultiversX", "tier": "emerging", "type": "smart_platform", "market_cap_rank": 43},
    {"symbol": "THETA-USD", "name": "Theta Network", "tier": "emerging", "type": "video_streaming", "market_cap_rank": 44},
    {"symbol": "AXS-USD", "name": "Axie Infinity", "tier": "emerging", "type": "gaming", "market_cap_rank": 45},
    {"symbol": "CHZ-USD", "name": "Chiliz", "tier": "emerging", "type": "sports_fan", "market_cap_rank": 46},
    {"symbol": "ENJ-USD", "name": "Enjin Coin", "tier": "emerging", "type": "gaming_nft", "market_cap_rank": 47},
    {"symbol": "BAT-USD", "name": "Basic Attention Token", "tier": "emerging", "type": "digital_ads", "market_cap_rank": 48},
    {"symbol": "ZEC-USD", "name": "Zcash", "tier": "emerging", "type": "privacy", "market_cap_rank": 49},
    {"symbol": "COMP-USD", "name": "Compound", "tier": "emerging", "type": "defi", "market_cap_rank": 50}
]

# FILTERING FUNCTIONS
def get_by_tier(tier_name):
    """Get cryptos by tier: blue_chip, major_alt, growth, emerging"""
    return [crypto for crypto in EXPANDED_CRYPTO_WATCHLIST if crypto["tier"] == tier_name]

def get_by_type(crypto_type):
    """Get cryptos by use case type"""
    return [crypto for crypto in EXPANDED_CRYPTO_WATCHLIST if crypto["type"] == crypto_type]

def get_top_n_by_market_cap(n=20):
    """Get top N cryptos by market cap ranking"""
    sorted_cryptos = sorted(EXPANDED_CRYPTO_WATCHLIST, key=lambda x: x["market_cap_rank"])
    return sorted_cryptos[:n]

def get_symbols_only(crypto_list=None):
    """Extract just the symbols from crypto list"""
    if crypto_list is None:
        crypto_list = EXPANDED_CRYPTO_WATCHLIST
    return [crypto["symbol"] for crypto in crypto_list]

def get_diversified_portfolio(max_per_tier=None):
    """Get a diversified crypto portfolio across tiers"""
    if max_per_tier is None:
        max_per_tier = {"blue_chip": 8, "major_alt": 10, "growth": 8, "emerging": 4}
    
    portfolio = []
    for tier, max_count in max_per_tier.items():
        tier_cryptos = get_by_tier(tier)
        # Sort by market cap rank within tier
        tier_cryptos.sort(key=lambda x: x["market_cap_rank"])
        portfolio.extend(tier_cryptos[:max_count])
    
    return portfolio

# MARKET CAP FILTERING (for dynamic updates)
def filter_by_market_cap_threshold(min_market_cap_billions=1.0):
    """
    Filter cryptos by minimum market cap threshold
    Note: This would require real-time API data to work properly
    """
    # Placeholder - in real implementation, would fetch live market cap data
    # For now, use market cap rank as proxy (rank < 30 = likely > 1B market cap)
    threshold_rank = 30 if min_market_cap_billions >= 1.0 else 50
    return [crypto for crypto in EXPANDED_CRYPTO_WATCHLIST if crypto["market_cap_rank"] <= threshold_rank]

# USAGE EXAMPLES
if __name__ == "__main__":
    print("=== EXPANDED CRYPTO WATCHLIST ===")
    print(f"Total cryptos: {len(EXPANDED_CRYPTO_WATCHLIST)}")
    print(f"Blue chip (Top 10): {len(get_by_tier('blue_chip'))}")
    print(f"Major altcoins: {len(get_by_tier('major_alt'))}")
    print(f"Growth coins: {len(get_by_tier('growth'))}")
    print(f"Emerging: {len(get_by_tier('emerging'))}")
    print()
    
    print("=== DIVERSIFIED PORTFOLIO (30 cryptos) ===")
    diversified = get_diversified_portfolio()
    print(f"Portfolio size: {len(diversified)}")
    for crypto in diversified:
        print(f"  {crypto['symbol']:15} | {crypto['name']:20} | Rank #{crypto['market_cap_rank']:2} | {crypto['type']}")
    print()
    
    print("=== SYMBOLS ONLY FOR TRADING ===")
    symbols = get_symbols_only(diversified)
    print(f"Symbols list: {symbols}")