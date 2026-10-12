
import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error

TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
USER_ID = os.environ["INSTAGRAM_USER_ID"]
API_VERSION = "v24.0"
BASE = f"https://graph.instagram.com/{API_VERSION}"


def request(method, endpoint, params):
    url = f"{BASE}/{endpoint}"
    data = urllib.parse.urlencode(params).encode()

    if method == "GET":
        url += "?" + data.decode()
        req = urllib.request.Request(url)
    else:
        req = urllib.request.Request(url, data=data, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        print("Instagram API error:", error.read().decode())
        raise


with open("instagram_carousel_manifest.json", encoding="utf-8") as file:
    manifest = json.load(file)

if manifest.get("publish_enabled") is not False:
    raise RuntimeError("Safety check failed: publishing must be disabled.")

slides = manifest["slides"]

if len(slides) != 5:
    raise RuntimeError("Expected exactly five carousel slides.")

print("Testing Instagram carousel media creation.")
print("Publishing is DISABLED.")

container_ids = []

for slide in slides:
    result = request(
        "POST",
        f"{USER_ID}/media",
        {
            "image_url": slide["image_url"],
            "is_carousel_item": "true",
            "access_token": TOKEN,
        },
    )

    container_id = result["id"]
    container_ids.append(container_id)
    print(f"Slide {slide['slide']}: container created")

    for attempt in range(10):
        time.sleep(3)

        status = request(
            "GET",
            container_id,
            {
                "fields": "status_code",
                "access_token": TOKEN,
            },
        )

        state = status.get("status_code")
        print(f"  Processing status: {state}")

        if state == "FINISHED":
            break

        if state in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Slide processing failed: {state}")
    else:
        raise RuntimeError("Slide processing timed out.")

print("All five image containers are ready.")

carousel = request(
    "POST",
    f"{USER_ID}/media",
    {
        "media_type": "CAROUSEL",
        "children": ",".join(container_ids),
        "caption": "MarketRevamp daily news briefing — TEST ONLY",
        "access_token": TOKEN,
    },
)

print("Carousel container created successfully.")
print("Carousel container ID:", carousel["id"])
print("NOT PUBLISHED. No /media_publish request was made.")
