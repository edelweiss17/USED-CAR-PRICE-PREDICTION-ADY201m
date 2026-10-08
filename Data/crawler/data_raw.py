import argparse
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import requests

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

bounds = [
    0, 100000000, 200000000, 300000000, 400000000, 500000000,
    600000000, 800000000, 1000000000, 1500000000, 2500000000, 1000000000000
]


def fetch_ads(params):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(ENDPOINT, params=params, headers=headers, timeout=15)
        if res.status_code == 200:
            return res.json().get("ads", []), res.url
        if res.status_code == 429:
            time.sleep(60)
    except requests.RequestException:
        pass
    return [], ""


def parse_ad(ad, source_url):
    row = {}
    for k in FIELDS:
        val = ad.get(k)
        if isinstance(val, list):
            val = json.dumps(val, ensure_ascii=False)
        row[k] = val
    row["source_url"] = source_url
    row["fetched_at"] = datetime.now(timezone.utc).isoformat()
    return row


def crawl(target=15000, delay=1.0, out_dir="data"):
    out_path = Path(out_dir)
    if not out_path.is_absolute():
        out_path = Path(__file__).resolve().parent / out_dir
    out_path.mkdir(parents=True, exist_ok=True)
    csv_file = out_path / "cars.csv"

    columns = FIELDS + ["source_url", "fetched_at"]
    seen_ids = set()

    if csv_file.exists() and csv_file.stat().st_size > 0:
        with open(csv_file, mode="r", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                if r.get("list_id"):
                    seen_ids.add(str(r["list_id"]))

    file_exists = csv_file.exists() and csv_file.stat().st_size > 0
    f = open(csv_file, mode="a", encoding="utf-8-sig", newline="")
    writer = csv.DictWriter(f, fieldnames=columns)
    if not file_exists:
        writer.writeheader()

    print(f"Bat dau thu thap. Da co: {len(seen_ids)}, Muc tieu: {target}")

    for low, high in zip(bounds, bounds[1:]):
        if len(seen_ids) >= target:
            break

        price_range = f"{low}-{high - 1}"
        offset = 0
        stalled = 0

        while len(seen_ids) < target:
            params = {
                "cg": 2010,
                "condition_ad": 1,
                "st": "s,k",
                "limit": 50,
                "o": offset,
                "price": price_range,
            }
            ads, url = fetch_ads(params)
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

            f.flush()
            offset += len(ads)
            print(f"Gia: {price_range} | Lay moi: {new_count} | Tong: {len(seen_ids)}/{target}")

            if new_count == 0:
                stalled += 1
                if stalled >= 3:
                    break
            else:
                stalled = 0

            if len(ads) < 50:
                break

            time.sleep(delay)

    f.close()
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
