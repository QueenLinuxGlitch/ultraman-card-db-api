#!/usr/bin/env python3
"""
Download images listed in a CSV using the requests library, and convert them to PNG.

Expected CSV columns (case-insensitive):
- image_url : the URL of the image to download
- name      : name to use in the output filename
- number    : number to use in the output filename

Output filename format: {name}_{number}.png
Files are saved into the "image_download" directory (configurable).
A delay (default 5 seconds) is enforced between each *download* (skips do not delay).
If a target filename already exists and --overwrite is not set, the download is skipped.

Usage:
    python download_images.py /path/to/images.csv
    # Optional args:
    #   --outdir image_download
    #   --delay 5
    #   --overwrite
"""

import argparse
import csv
import logging
import mimetypes
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from PIL import Image


ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif", ".ico", ".bin"}


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def sanitize_component(value: str, max_len: int = 150) -> str:
    if value is None:
        value = ""
    value = str(value).strip()
    value = value.replace(" ", "_")
    value = re.sub(r"[^A-Za-z0-9._-]", "", value)
    value = re.sub(r"[_\.-]{2,}", lambda m: m.group(0)[0], value)
    if not value:
        value = "unnamed"
    return value[:max_len]


def infer_ext_from_url(url: str) -> Optional[str]:
    path = urlparse(url).path
    if not path:
        return None
    name = Path(path).name
    ext = Path(name).suffix.lower()
    if ext in ALLOWED_IMAGE_EXTS:
        return ext
    return None


def infer_ext_from_content_type(content_type: Optional[str]) -> str:
    if content_type is None:
        return ".bin"
    ct = content_type.split(";")[0].strip().lower()
    mapping = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/bmp": ".bmp",
        "image/webp": ".webp",
        "image/tiff": ".tiff",
        "image/x-icon": ".ico",
        "image/vnd.microsoft.icon": ".ico",
        "application/octet-stream": ".bin",
    }
    return mapping.get(ct, mimetypes.guess_extension(ct) or ".bin")


def build_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.8,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(
        {
            "User-Agent": "image-downloader/1.2 (+https://example.com)",
            "Accept": "*/*",
        }
    )
    return session


def normalize_headers_keys(row: Dict[str, str]) -> Dict[str, str]:
    return { (k.lower() if isinstance(k, str) else k): v for k, v in row.items() }


def convert_to_png(image_path: Path, outdir: Path, base_stem: str, overwrite: bool = False) -> Path:
    try:
        img = Image.open(image_path).convert("RGBA")
        png_path = outdir / f"{base_stem}.png"
        if png_path.exists() and not overwrite:
            logging.info("PNG already exists, skipping conversion: %s", png_path.name)
            return png_path
        img.save(png_path, "PNG")
        logging.info("Converted to PNG: %s", png_path.name)
        return png_path
    except Exception as e:
        logging.error("PNG conversion failed for %s: %s", image_path.name, e)
        return image_path


def download_images_from_csv(csv_path: Path, outdir: Path, delay: float = 2.0, overwrite: bool = False) -> None:
    if not csv_path.exists():
        logging.error("CSV not found: %s", csv_path)
        sys.exit(1)

    outdir.mkdir(parents=True, exist_ok=True)
    session = build_session()

    with csv_path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            logging.error("CSV appears to have no header row.")
            sys.exit(1)

        headers_lc = [h.lower() for h in reader.fieldnames]
        required_cols = ["image_url", "name", "number"]
        missing = [c for c in required_cols if c not in headers_lc]
        if missing:
            logging.error("CSV is missing required columns: %s", ", ".join(missing))
            sys.exit(1)

        total = 0
        successes = 0
        failures = 0
        skips = 0

        for idx, row in enumerate(reader, start=1):
            total += 1
            row_lc = normalize_headers_keys(row)
            url = (row_lc.get("image_url") or "").strip()
            name_val = row_lc.get("name")
            number_val = row_lc.get("number")

            if not url:
                logging.warning("Row %d skipped: empty image_url", idx)
                failures += 1
                continue

            base_stem = f"{sanitize_component(name_val)}_{sanitize_component(number_val)}"
            ext_from_url = infer_ext_from_url(url)

            # PNG path target
            png_target = outdir / f"{base_stem}.png"
            if png_target.exists() and not overwrite:
                logging.info("(%d) Skipping (PNG already exists): %s", idx, png_target.name)
                skips += 1
                continue

            # Download original
            try:
                logging.info("(%d) GET %s", idx, url)
                with session.get(url, stream=True, timeout=20) as resp:
                    if resp.status_code != 200:
                        logging.error("Failed (%d): HTTP %s for %s", idx, resp.status_code, url)
                        failures += 1
                        if delay:
                            time.sleep(delay)
                        continue

                    ext = ext_from_url or infer_ext_from_content_type(resp.headers.get("Content-Type"))
                    tmp_path = outdir / f"{base_stem}{ext}"
                    with tmp_path.open("wb") as outf:
                        for chunk in resp.iter_content(chunk_size=8192):
                            if chunk:
                                outf.write(chunk)

                logging.info("Saved temp file: %s", tmp_path.name)
                # Convert to PNG
                convert_to_png(tmp_path, outdir, base_stem, overwrite=overwrite)
                successes += 1

            except requests.RequestException as e:
                logging.error("Request failed for row %d (%s): %s", idx, url, e)
                failures += 1
            except Exception as e:
                logging.error("Unexpected error row %d: %s", idx, e)
                failures += 1
            finally:
                if delay and idx >= 1 and (successes + failures) >= 1:
                    time.sleep(delay)

        logging.info("Done. Total: %d | PNGs created: %d | Skipped: %d | Failures: %d",
                     total, successes, skips, failures)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download images from a CSV and convert them to PNG.")
    parser.add_argument("csv_path", type=Path, help="Path to the CSV file (must include image_url, name, number columns).")
    parser.add_argument("--outdir", type=Path, default=Path("image_download"), help="Output directory for images.")
    parser.add_argument("--delay", type=float, default=5.0, help="Delay in seconds between each download (default 5.0).")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing PNG files.")
    return parser.parse_args()


def main():
    setup_logging()
    args = parse_args()
    download_images_from_csv(args.csv_path, args.outdir, args.delay, args.overwrite)


if __name__ == "__main__":
    main()
