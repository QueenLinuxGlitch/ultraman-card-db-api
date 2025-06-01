# card-db-meta.py

import requests
import csv

API_URL = "https://api.ultraman-cardgame.com/api/v1/us/cards"

OUTPUT_FILES = {
    'types': 'ultraman_types.csv',
    'features': 'ultraman_features.csv',
    'rarities': 'ultraman_rarities.csv',
    'grades': 'ultraman_grades.csv',
    'card_bundles': 'ultraman_card_bundles.csv',
}

META_FIELDS = list(OUTPUT_FILES.keys())

def fetch_api_metadata():
    resp = requests.get(API_URL)
    resp.raise_for_status()
    meta = resp.json().get('meta', {})
    return {field: meta.get(field, []) for field in META_FIELDS}

def save_simple_meta_to_csv(data, filename, field):
    rows = []
    for entry in data:
        row = {k: v for k, v in entry.items() if isinstance(v, (str, int, float))}
        rows.append(row)
    if rows:
        fieldnames = list(rows[0].keys())
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Saved {len(rows)} rows to {filename}")
    else:
        print(f"No data for {field}, nothing saved.")

def save_card_bundles_to_csv(data, filename):
    rows = []
    for bundle in data:
        detail = bundle.get('detail', {})
        row = {
            'id': bundle.get('id'),
            'type': bundle.get('type', {}).get('description'),
            'version': bundle.get('version'),
            'name': detail.get('name'),
            'display_name': detail.get('display_name'),
            'caption_name': detail.get('caption_name'),
            'price': detail.get('price'),
            'released_at': detail.get('released_at'),
        }
        rows.append(row)
    if rows:
        fieldnames = list(rows[0].keys())
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Saved {len(rows)} rows to {filename}")
    else:
        print(f"No data for card_bundles, nothing saved.")

def main():
    meta = fetch_api_metadata()
    for field in META_FIELDS:
        filename = OUTPUT_FILES[field]
        if field == 'card_bundles':
            save_card_bundles_to_csv(meta[field], filename)
        else:
            save_simple_meta_to_csv(meta[field], filename, field)

if __name__ == "__main__":
    main()
