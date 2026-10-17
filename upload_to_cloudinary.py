from carousel_config import CAROUSEL_SIZE
"""Upload MarketRevamp's generated PNG slides to Cloudinary.

Requires CLOUDINARY_CLOUD_NAME and CLOUDINARY_UPLOAD_PRESET environment variables.
Only uploads images; does not publish or schedule social media posts.
"""
import json
import mimetypes
import os
import secrets
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

IMAGES = Path('instagram_images')
OUTPUT = Path('cloudinary_uploads.json')


def upload_image(path, cloud, preset):
    boundary = '----MarketRevamp' + secrets.token_hex(12)
    fields = [('upload_preset', preset), ('file', path.read_bytes())]
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
    if not cloud or not preset:
        raise SystemExit('Missing CLOUDINARY_CLOUD_NAME or CLOUDINARY_UPLOAD_PRESET environment variable')
    paths = sorted(IMAGES.glob('slide_*.png'))
    if len(paths) != CAROUSEL_SIZE:
        raise SystemExit(f'Expected exactly seven slide PNGs, found {len(paths)}. No upload attempted.')
    uploaded = []
    try:
        for path in paths:
            result = upload_image(path, cloud, preset)
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
