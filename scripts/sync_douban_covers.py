import csv
import io
import os
import time
import random
import requests
from PIL import Image
import boto3

# -------- B2 S3 config (fill yours) --------
B2_ENDPOINT = "https://s3.us-west-004.backblazeb2.com"  # example
B2_KEY_ID = os.environ.get("B2_KEY_ID")
B2_APP_KEY = os.environ.get("B2_APP_KEY")
B2_BUCKET = "marryhasalittlesheemississipi"
B2_PREFIX = "douban-covers"  # folder in bucket

s3 = boto3.client(
    "s3",
    endpoint_url=B2_ENDPOINT,
    aws_access_key_id=B2_KEY_ID,
    aws_secret_access_key=B2_APP_KEY,
)

HEADERS = {
    # Referer 有时能提高豆瓣图成功率，但不保证；也可能无效
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://book.douban.com/",
}


def download_image(url: str) -> bytes:
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.content

def to_webp(img_bytes: bytes, quality=82) -> bytes:
    im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    out = io.BytesIO()
    im.save(out, format="WEBP", quality=quality, method=6)
    return out.getvalue()

def upload_webp(key: str, webp_bytes: bytes) -> str:
    s3.put_object(
        Bucket=B2_BUCKET,
        Key=key,
        Body=webp_bytes,
        ContentType="image/webp",
        # ACL="public-read",
        CacheControl="public, max-age=31536000, immutable",
    )
    # public URL pattern depends on your setup; common S3-style:
    return f"{B2_ENDPOINT}/{B2_BUCKET}/{key}"

def main():
    with open("books.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        #print("FIELDNAMES:", reader.fieldnames)

        for row in reader:
            slug = row["slug"].strip()
            url = row["douban_image_url"].strip()
            print("AFTER STRIP:", repr(slug), repr(url))
            #print("ROWS:", len(row))
            if not slug or not url:
                print("SKIP empty row")
                continue

            key = f"{B2_PREFIX}/{slug}.webp"
            print("Processing:", slug)

            try:
                img = download_image(url)
                print("Downloaded bytes:", len(img))

                webp = to_webp(img)
                print("Webp bytes:", len(webp))

                out_url = upload_webp(key, webp)
                print("OK:", out_url)
            except Exception as e:
                print("FAIL:", slug, e)

            # polite delay (avoid hammering)
            time.sleep(random.uniform(0.6, 1.6))

if __name__ == "__main__":
    main()
