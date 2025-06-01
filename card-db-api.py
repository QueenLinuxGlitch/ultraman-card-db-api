# card-db-api.py

import csv
import time
import os
import requests

API_BASE_URL = "https://api.ultraman-cardgame.com/api/v1/us/cards"
OUTPUT_CSV = "ultraman_cards.csv"
SLEEP_BETWEEN_REQUESTS = 0.3  # To avoid hammering the API

FIELDNAMES = [
    'id', 'name', 'type_name', 'character_name', 'rarity', 'type', 'feature', 'level',
    'battle_power_1', 'battle_power_2', 'battle_power_3', 'battle_power_ex',
    'effect', 'flavor_text', 'section', 'bundle_version', 'serial', 'branch',
    'number', 'participating_works', 'publication_year', 'illustrator_name', 'image_url', 'thumbnail_image_url'
]

def extract_card_data(card):
    detail = card.get('detail', {})
    return {
        'id': card.get('id'),
        'name': detail.get('name'),
        'type_name': detail.get('type_name'),
        'character_name': detail.get('character_name'),
        'rarity': card.get('rarity', {}).get('description'),
        'type': card.get('type', {}).get('description') if card.get('type') else None,
        'feature': card.get('feature', {}).get('description') if card.get('feature') else None,
        'level': card.get('level'),
        'battle_power_1': card.get('battle_power_1'),
        'battle_power_2': card.get('battle_power_2'),
        'battle_power_3': card.get('battle_power_3'),
        'battle_power_ex': card.get('battle_power_ex'),
        'effect': detail.get('effect'),
        'flavor_text': detail.get('flavor_text'),
        'section': card.get('section'),
        'bundle_version': card.get('bundle_version'),
        'serial': card.get('serial'),
        'branch': card.get('branch'),
        'number': card.get('number'),
        'participating_works': detail.get('participating_works'),
        'publication_year': card.get('publication_year'),
        'illustrator_name': detail.get('illustrator_name'),
        'image_url': detail.get('image_url'),
        'thumbnail_image_url': detail.get('thumbnail_image_url')
    }

def get_all_cards():
    all_cards = []
    next_url = API_BASE_URL
    page = 1
    while next_url:
        print(f"Fetching page {page}...")
        resp = requests.get(next_url)
        resp.raise_for_status()
        data = resp.json()
        cards = data.get('data', [])
        all_cards.extend(cards)
        next_url = data.get('links', {}).get('next')
        page += 1
        time.sleep(SLEEP_BETWEEN_REQUESTS)
    return all_cards

def save_cards_to_csv(cards, filename):
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
        writer.writeheader()
        for card in cards:
            row = extract_card_data(card)
            writer.writerow(row)
    print(f"Saved {len(cards)} cards to {filename}")

def copy_file_to_directory(src, dst_dir):
    if not os.path.isdir(dst_dir):
        raise FileNotFoundError(f"Destination directory not found: {dst_dir}")

    dst = os.path.join(dst_dir, os.path.basename(src))

    with open(src, 'rb') as fsrc:
        with open(dst, 'wb') as fdst:
            fdst.write(fsrc.read())
    return dst

if __name__ == "__main__":
    cards = get_all_cards()
    save_cards_to_csv(cards, OUTPUT_CSV)
    copy_file_to_directory('ultraman_cards.csv','docs/')
