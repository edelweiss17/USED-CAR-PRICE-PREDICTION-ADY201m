import argparse
import csv
import json
from pathlib import Path
import sys
import time
from datetime import datetime, timezone
import requests

sys.dont_write_bytecode = True

ENDPOINT = "https://gateway.chotot.com/v1/public/ad-listing"

FIELDS = [
    "list_id", "ad_id", "subject", "price", "price_string",
    "category", "category_name", "condition_ad", "condition_ad_name",
    "carbrand", "carbrand_name", "carmodel", "carmodel_name",
    "mfdate", "mileage_v2", "gearbox", "fuel", "carseats",
    "cartype", "carcolor", "carorigin", "region_v2", "region_name",
    "region_name_v3", "area_name", "ward_name", "list_time",
    "orig_list_time", "image", "images", "number_of_images",
    "type", "status"
]

PRICE_BOUNDS = [
    0,
    100_000_000,
    200_000_000,
    300_000_000,
    400_000_000,
    500_000_000,
    600_000_000,
    800_000_000,
    1_000_000_000,
    1_500_000_000,
    2_500_000_000,
    1_000_000_000_000,
]


def load_crawled_ids(csv_file):
    seen_ids = set()
    if csv_file.exists() and csv_file.stat().st_size > 0:
        with open(csv_file, mode="r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                list_id = row.get("list_id")
                if list_id:
                    seen_ids.add(str(list_id))
    return seen_ids


def fetch_ads(session, params, max_retries=3):
    for attempt in range(max_retries):
        try:
            res = session.get(ENDPOINT, params=params, timeout=15)
            if res.status_code == 200:
                return res.json().get("ads", []), res.url
            if res.status_code == 429:
                time.sleep(15 * (attempt + 1))
                continue
        except requests.RequestException:
            time.sleep(2 * (attempt + 1))
    return [], ""


def parse_ad(ad, source_url):
    row = {}
    for key in FIELDS:
        val = ad.get(key)
        if isinstance(val, (list, dict)):
            val = json.dumps(val, ensure_ascii=False)
        row[key] = val
    row["source_url"] = source_url
    row["fetched_at"] = datetime.now(timezone.utc).isoformat()
    return row


def crawl_price_range(session, low, high, seen_ids, writer, file_obj, target, delay):
    price_range = f"{low}-{high - 1}"
    offset = 0
    stalled_count = 0

    while len(seen_ids) < target:
        params = {
            "cg": 2010,
            "condition_ad": 1,
            "st": "s,k",
            "limit": 50,
            "o": offset,
            "price": price_range,
        }
        ads, url = fetch_ads(session, params)
        if not ads:
            break

        new_count = 0
        for ad in ads:
            list_id = str(ad.get("list_id", ""))
            if not list_id or list_id in seen_ids:
                continue

            writer.writerow(parse_ad(ad, url))
            seen_ids.add(list_id)
            new_count += 1
            if len(seen_ids) >= target:
                break

        file_obj.flush()
        offset += len(ads)
        print(f"Gia: {price_range} | Lay moi: {new_count} | Tong: {len(seen_ids)}/{target}")

        if new_count == 0:
            stalled_count += 1
            if stalled_count >= 3:
                break
        else:
            stalled_count = 0

        if len(ads) < 50:
            break

        time.sleep(delay)


def crawl(target=15000, delay=1.0, out_dir="data"):
    out_path = Path(out_dir)
    if not out_path.is_absolute():
        out_path = Path(__file__).resolve().parent / out_dir
    out_path.mkdir(parents=True, exist_ok=True)
    csv_file = out_path / "cars.csv"

    columns = FIELDS + ["source_url", "fetched_at"]
    seen_ids = load_crawled_ids(csv_file)
    file_exists = csv_file.exists() and csv_file.stat().st_size > 0

    print(f"Bat dau thu thap. Da co: {len(seen_ids)}, Muc tieu: {target}")
    if len(seen_ids) >= target:
        print("Da dat chi tieu, khong can thu thap them.")
        return

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

    with open(csv_file, mode="a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        if not file_exists:
            writer.writeheader()

        for low, high in zip(PRICE_BOUNDS, PRICE_BOUNDS[1:]):
            if len(seen_ids) >= target:
                break

            crawl_price_range(
                session=session,
                low=low,
                high=high,
                seen_ids=seen_ids,
                writer=writer,
                file_obj=f,
                target=target,
                delay=delay,
            )

    print(f"Hoan tat! Tong tin: {len(seen_ids)} tai {csv_file}")


def main():
    parser = argparse.ArgumentParser(description="Thu thap du lieu xe cu Cho Tot")
    parser.add_argument("--target", type=int, default=15000)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--out", default="data")
    args = parser.parse_args()

    crawl(target=args.target, delay=args.delay, out_dir=args.out)


if __name__ == "__main__":
    main()
