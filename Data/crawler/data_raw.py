import argparse
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ENDPOINT = 'https://gateway.chotot.com/v1/public/ad-listing'
FIELDS = ('list_id ad_id subject price price_string category category_name condition_ad '
          'condition_ad_name carbrand carbrand_name carmodel carmodel_name mfdate '
          'mileage_v2 gearbox fuel carseats cartype carcolor carorigin region_v2 '
          'region_name region_name_v3 area_name ward_name list_time orig_list_time '
          'image images number_of_images type status').split()

bounds = [0, 100000000, 200000000, 300000000, 400000000, 500000000,
          600000000, 800000000, 1000000000, 1500000000, 2500000000, 1000000000000]

def fetch(params):
    url = f"{ENDPOINT}?{urlencode(params)}"
    req = Request(url, headers={'User-Agent': 'UsedCarResearch/1.0', 'Accept': 'application/json'})
    for attempt in range(5):
        try:
            with urlopen(req, timeout=45) as res:
                data = json.load(res)
            if isinstance(data.get('ads'), list):
                return data, url
            raise ValueError('Response missing ads array')
        except HTTPError as err:
            if err.code == 429:
                delay = int(err.headers.get('Retry-After', 60))
                time.sleep(max(60, delay))
            elif err.code >= 500 and attempt < 4:
                time.sleep(5 * (attempt + 1))
            else:
                raise
        except (URLError, TimeoutError):
            if attempt == 4:
                raise
            time.sleep(5 * (attempt + 1))
    raise RuntimeError('Retry limit reached')

def clean_val(v):
    if isinstance(v, list):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + v
    return v

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', type=int, default=15000)
    parser.add_argument('--delay', type=float, default=1.5)
    parser.add_argument('--out', default='data')
    args = parser.parse_args()

    out = Path(args.out) if Path(args.out).is_absolute() else Path(__file__).resolve().parent / args.out
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / 'cars.csv'

    cols = list(FIELDS) + ['source_url', 'fetched_at']
    seen_ids = set()
    file_exists = csv_path.exists() and csv_path.stat().st_size > 0

    if file_exists:
        with csv_path.open('r', encoding='utf-8-sig', newline='') as f:
            for r in csv.DictReader(f):
                lid = r.get('list_id')
                if lid:
                    seen_ids.add(str(lid))

    total = len(seen_ids)
    print(f'Starting with {total} existing records. Target: {args.target}', flush=True)

    with csv_path.open('a' if file_exists else 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        if not file_exists:
            writer.writeheader()
            f.flush()

        for low, high in zip(bounds, bounds[1:]):
            if total >= args.target:
                break
            source = f'{low}-{high - 1}'
            offset = 0
            stalled = 0

            while total < args.target:
                time.sleep(args.delay)
                res, url = fetch({'cg': 2010, 'condition_ad': 1, 'st': 's,k', 'limit': 50, 'o': offset, 'price': source})
                ads = res.get('ads', [])
                if not ads:
                    break

                now = datetime.now(timezone.utc).isoformat()
                new = 0
                for ad in ads:
                    if total >= args.target:
                        break
                    list_id = str(ad.get('list_id'))
                    if not list_id or list_id in seen_ids:
                        continue
                    if ad.get('category') != 2010 or ad.get('condition_ad') != 1 or not (low <= ad.get('price', -1) < high):
                        continue

                    row = {k: clean_val(ad.get(k)) for k in FIELDS}
                    row['source_url'] = url
                    row['fetched_at'] = now
                    writer.writerow(row)
                    seen_ids.add(list_id)
                    total += 1
                    new += 1

                offset += len(ads)
                f.flush()
                print(f'price={source} offset={offset} new={new} total={total}/{args.target}', flush=True)

                stalled = stalled + 1 if new == 0 else 0
                if stalled >= 5:
                    break

    print(f'Done. Total records: {total} saved to {csv_path}', flush=True)
    return 0 if total >= args.target else 2

if __name__ == '__main__':
    raise SystemExit(main())
