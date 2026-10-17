"""Upload MarketRevamp's generated PNG slides to Cloudinary.

Requires CLOUDINARY_CLOUD_NAME and CLOUDINARY_UPLOAD_PRESET environment variables.
Only uploads images; does not publish or schedule social media posts.
"""

from carousel_config import CAROUSEL_SIZE

import json
import hashlib
import time
import mimetypes
import os
import secrets
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

IMAGES = Path('instagram_images')
OUTPUT = Path('cloudinary_uploads.json')


def upload_fields(preset, api_key="", api_secret="", timestamp=None):
    """Build Cloudinary signed fields when both credentials are configured."""
    if bool(api_key) != bool(api_secret):
        raise ValueError("Cloudinary signed upload requires both API key and API secret.")
    fields = [("upload_preset", preset)]
    if api_key:
        timestamp = int(time.time()) if timestamp is None else int(timestamp)
        signature_base = f"timestamp={timestamp}&upload_preset={preset}"
        signature = hashlib.sha1(
            (signature_base + api_secret).encode("utf-8")
        ).hexdigest()
        fields.extend([
            ("timestamp", str(timestamp)),
            ("api_key", api_key),
            ("signature", signature),
        ])
    return fields


def upload_image(path, cloud, preset, api_key="", api_secret=""):
    boundary = '----MarketRevamp' + secrets.token_hex(12)
    fields = upload_fields(preset, api_key, api_secret) + [('file', path.read_bytes())]
    body = bytearray()
    for name, value in fields:
        body.extend(f'--{boundary}\r\n'.encode())
        if name == 'file':
            body.extend(f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'.encode())
            body.extend(b'Content-Type: image/png\r\n\r\n')
            body.extend(value)
        else:
            body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}'.encode())
        body.extend(b'\r\n')
    body.extend(f'--{boundary}--\r\n'.encode())
    request = urllib.request.Request(
        f'https://api.cloudinary.com/v1_1/{cloud}/image/upload',
        data=bytes(body),
        headers={'Content-Type': f'multipart/form-data; boundary={boundary}', 'User-Agent': 'MarketRevamp/1.0'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read(1000).decode('utf-8', errors='replace')
        raise RuntimeError(f'Cloudinary rejected {path.name} (HTTP {exc.code}): {detail}') from exc
    url = result.get('secure_url')
    if not isinstance(url, str) or not url.startswith('https://res.cloudinary.com/'):
        raise RuntimeError(f'Cloudinary returned no valid secure_url for {path.name}')
    return {'slide': path.name, 'secure_url': url, 'public_id': result.get('public_id')}


def main():
    cloud = os.environ.get('CLOUDINARY_CLOUD_NAME', '').strip()
    preset = os.environ.get('CLOUDINARY_UPLOAD_PRESET', '').strip()
    api_key = os.environ.get('CLOUDINARY_API_KEY', '').strip()
    api_secret = os.environ.get('CLOUDINARY_API_SECRET', '').strip()
    if bool(api_key) != bool(api_secret):
        raise SystemExit('Both Cloudinary API key and API secret are required for signed uploads')
    if not cloud or not preset:
        raise SystemExit('Missing CLOUDINARY_CLOUD_NAME or CLOUDINARY_UPLOAD_PRESET environment variable')
    paths = sorted(IMAGES.glob('slide_*.png'))
    if len(paths) != CAROUSEL_SIZE:
        raise SystemExit(f'Expected exactly seven slide PNGs, found {len(paths)}. No upload attempted.')
    uploaded = []
    try:
        for path in paths:
            result = upload_image(path, cloud, preset, api_key, api_secret)
            uploaded.append(result)
            print(f'Uploaded {path.name} -> {result["secure_url"]}')
    finally:
        # Preserve URLs for any successful uploads even if a later upload fails.
        if uploaded:
            OUTPUT.write_text(json.dumps({'uploaded_at': datetime.now(timezone.utc).isoformat(), 'images': uploaded}, indent=2), encoding='utf-8')
    print(f'Saved {len(uploaded)} public image URLs to {OUTPUT}')
    print('No Instagram posts or Metricool drafts created.')


if __name__ == '__main__':
    main()
