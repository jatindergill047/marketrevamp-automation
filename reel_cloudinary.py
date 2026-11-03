"""Upload optional Reel MP4 media to Cloudinary; no Instagram actions."""
import json
import urllib.parse
import urllib.request
from pathlib import Path
from upload_to_cloudinary import upload_fields


def upload_video(path, cloud, preset, api_key="", api_secret=""):
    source = Path(path)
    if not source.is_file() or source.suffix.lower() != ".mp4" or source.stat().st_size == 0:
        raise ValueError("Expected a nonempty MP4 file")
    if not cloud or not preset or "/" in cloud:
        raise ValueError("Missing or invalid Cloudinary configuration")
    boundary = "MarketRevampReelBoundary"
    body = bytearray()
    for key, value in upload_fields(preset, api_key, api_secret):
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="reel.mp4"\r\nContent-Type: video/mp4\r\n\r\n'.encode())
    body.extend(source.read_bytes())
    body.extend(f'\r\n--{boundary}--\r\n'.encode())
    request = urllib.request.Request(
        f"https://api.cloudinary.com/v1_1/{cloud}/video/upload",
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        result = json.load(response)
    url = result.get("secure_url", "")
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "res.cloudinary.com" or not parsed.path.endswith(".mp4"):
        raise ValueError("Cloudinary returned an invalid MP4 URL")
    return {"secure_url": url, "public_id": result.get("public_id"), "resource_type": "video"}
