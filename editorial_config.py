"""Editorial sources, topic vocabulary, and length limits for MarketRevamp.

Change these values through a reviewed pull request; no live API calls here.
A carousel always requires seven distinct, source-screened articles.
"""

FEEDS = {
    "AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "Technology": "https://feeds.arstechnica.com/arstechnica/index",
    "Crypto": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Markets": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "BBC Technology": "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "BBC Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
}

FEED_CATEGORY = {"BBC Technology": "Technology", "BBC Business": "Markets"}

HEADERS = {"User-Agent": "MarketRevampNewsCollector/1.0"}

KEYWORDS = {
    "AI": [
        "artificial intelligence", " ai ", "ai’s", "ai-", "openai", "chatgpt",
        "anthropic", "claude", "gemini", "nvidia", "machine learning",
        "llm", "gpu", "data center", "datacenter", "robotics",
        "neural network", "ai model", "ai agent",
    ],
    "Technology": [
        "apple", "google", "microsoft", "amazon", "meta", "tesla",
        "semiconductor", "chipmaker", "microchip", "software",
        "cybersecurity", "cloud computing", "quantum computing",
        "startup", "technology", "smartphone", "iphone", "android",
        "computing", "robot", "product launch",
    ],
    "Crypto": [
        "bitcoin", "btc", "ethereum", "ether", "crypto", "blockchain",
        "stablecoin", "tokenized", "tokenization", "defi", "solana",
        "coinbase", "digital asset", "web3", "prediction market",
    ],
    "Markets": [
        "stock", "shares", "nasdaq", "s&p 500", "dow jones",
        "earnings", "inflation", "federal reserve", "interest rate",
        "bond", "treasury", "fixed income", "jpmorgan", "goldman sachs",
        "wall street", "investment", "investor", "401(k)",
        "private funds", "retailers", "retail sales", "economic growth",
        "recession", "oil prices", "gold prices", "commodities",
        "tariff", "ipo", "equity market",
    ],
}

EXCLUDE = [
    "celebrity", "fashion", "football", "soccer", "recipe",
    "wedding", "movie review", "press secretary", "houthi", "ceasefire",
]


# Summary length is shared with editorial validation.
SUMMARY_MIN_WORDS = 30
SUMMARY_MAX_WORDS = 90


