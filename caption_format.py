"""MarketRevamp Instagram caption formatting; no external API calls."""

HASHTAGS = "#MarketRevamp #AI #Technology #Crypto #Bitcoin #StockMarket"
CAPTION_LIMIT = 2200


def compose_caption(lines):
    """Keep article attribution and disclosures, then place hashtags last."""
    caption = "\n".join(lines).rstrip() + "\n\n" + HASHTAGS
    if len(caption) > CAPTION_LIMIT:
        raise ValueError("Instagram caption exceeds 2,200 characters.")
    return caption
