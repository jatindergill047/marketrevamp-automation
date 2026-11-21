"""Validate opt-in release state *without* contacting Instagram.

Production media still requires the exact R83 policy, latest cross-carousel
history, same-day source job, and Instagram readback.
"""
import re

POLICY="owner_authorized_source_attribution_v1"


def rollout_state_valid(state):
    if not isinstance(state,dict) or state.get("policy")!=POLICY or state.get("owner_authorized") is not True:
        raise ValueError("Owner authorization missing")
    first=state.get("controlled_first_live")
    daily=state.get("daily_enabled")
    if not isinstance(first,bool) or not isinstance(daily,bool) or (first and daily):
        raise ValueError("First-live and daily release stages must be separate")
    sha=state.get("first_video_sha256")
    media_id=state.get("verified_first_media_id")
    if first:
        if not isinstance(sha,str) or not re.fullmatch(r"[a-f0-9]{64}",sha) or media_id is not None:
            raise ValueError("First-live requires exact video SHA with no prior verified ID")
        return "first"
    if daily:
        if not isinstance(sha,str) or not re.fullmatch(r"[a-f0-9]{64}",sha):
            raise ValueError("Daily state missing first approved video audit SHA")
        if not isinstance(media_id,str) or not media_id.isdigit():
            raise ValueError("Daily mode requires real first-live Instagram media ID")
        return "daily"
    if sha is not None or media_id is not None:
        raise ValueError("Disabled stage cannot have first-release credentials")
    return "disabled"
