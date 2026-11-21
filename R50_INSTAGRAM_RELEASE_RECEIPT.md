# MarketRevamp R50 — First Live Instagram Reel Release Receipt

- **Published Toronto date:** 2026-11-20
- **Instagram account:** marketrevampdaily
- **Instagram Reel:** https://www.instagram.com/reel/Df_FmF_gT28/
- **Instagram media ID:** `17878336866585252`
- **Instagram creation container ID:** `18135107725801321`
- **Verified hosted MP4:** https://res.cloudinary.com/y0ln6ixr/video/upload/v1795225733/m4b8s2wthym8lzofbmnf.mp4
- **Approved MP4 SHA-256:** `532e450baff8d25b3ed50bc1a21882dba3eaf6c626c0af5066ca3cd74fdefb93`
- **Exact source+media+caption fingerprint:** `815ec5bbb6fac6beb36c9306c1fe08a3ee783781a88e509a9dd580138fbabc33`
- **Voice:** Microsoft Andrew Neural (`en-US-AndrewNeural`)
- **Format:** 1080×1920 H.264/AAC, 86.779 seconds
- **Stories:** 7 source-linked November 19–20 news items; duplicate news checks passed.

## Run evidence

1. [Exact video and full release fingerprint check](https://github.com/jatindergill047/marketrevamp-automation/actions/runs/44851655274): success.
2. [First live attempt](https://github.com/jatindergill047/marketrevamp-automation/actions/runs/44851854671): safely blocked **before upload or publication** because production signed Cloudinary secrets were absent.
3. [Cloudinary unsigned production-preset compatibility CI](https://github.com/jatindergill047/marketrevamp-automation/actions/runs/44852147635): success.
4. [One-time R50 live Instagram publication](https://github.com/jatindergill047/marketrevamp-automation/actions/runs/44852271492): success.
5. [Read-only Instagram Graph API verification](https://github.com/jatindergill047/marketrevamp-automation/actions/runs/44852532563): success, Instagram returned public permalink.

The authoritative `publishing-history` branch records `media_kind=reel`, `status=published`, and the returned Instagram media ID. Only direct Cloudinary hosting + Instagram Graph API were used; Metricool was not used.

## Separate future scope

**Recurring daily Reel publishing is not activated.** The November 20 approved package must not run on a later date or be reposted. A recurring workflow must create new, verified news stories and new video each publication day, enforce source freshness and duplicate checks, fail closed on publication ambiguity, and be separately tested before rollout. Existing carousel publishing remains unchanged.
