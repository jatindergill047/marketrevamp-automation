"""Manual-only Cloudinary staging upload smoke test. Never touches Instagram."""
import os
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from reel_cloudinary import upload_video

def main():
    for flag in ("REEL_ENABLED", "REEL_UPLOAD_ENABLED", "INSTAGRAM_PUBLISH_ENABLED"):
        if os.getenv(flag, "false").lower() == "true":
            raise RuntimeError("Staging forbids enabling Reel or Instagram publishing")
    cloud = os.environ["CLOUDINARY_CLOUD_NAME"]
    preset = os.environ["CLOUDINARY_UPLOAD_PRESET"]
    if preset != "marketrevamp_reels_staging":
        raise RuntimeError("Staging preset mismatch")
    key = os.environ["CLOUDINARY_API_KEY"]
    secret = os.environ["CLOUDINARY_API_SECRET"]
    if not key or not secret:
        raise RuntimeError("Signed staging credentials required")
    with tempfile.TemporaryDirectory(prefix="reel_stage_") as folder:
        video = Path(folder) / "synthetic_test.mp4"
        subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error",
                        "-f", "lavfi", "-i", "color=c=black:s=1080x1920:r=5",
                        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                        "-t", "2", "-c:v", "libx264", "-preset", "ultrafast",
                        "-pix_fmt", "yuv420p", "-c:a", "aac",
                        "-movflags", "+faststart", str(video)],
                       check=True, timeout=120)
        result = upload_video(video, cloud, preset, key, secret)
        url = result["secure_url"]
        parsed = urlsplit(url)
        if parsed.hostname != "res.cloudinary.com" or result["resource_type"] != "video":
            raise RuntimeError("Unexpected Cloudinary response")
        request = urllib.request.Request(url, headers={"Range": "bytes=0-1023"})
        with urllib.request.urlopen(request, timeout=60) as response:
            content = response.read(1024)
            status = response.status
        if status not in (200, 206) or not content:
            raise RuntimeError("Staging playback probe failed")
        print("STAGING VIDEO UPLOAD PASS: Cloudinary HTTPS playback reachable")
        print("Staging public_id:", result.get("public_id", "(missing)"))
        print("No Instagram publishing performed. Test media should be removed after review.")

if __name__ == "__main__":
    main()
