"""Prepare a validated Reel media payload without making network requests."""
from reel_security import validated_reel


def reel_payload(manifest):
    reel = validated_reel(manifest)
    return {
        "media_type": "REELS",
        "video_url": reel["video_url"],
        "caption": reel["caption"],
        "share_to_feed": "true",
    }
