#!/usr/bin/env python3
import os
import sys
import argparse
import requests
from bs4 import BeautifulSoup
import json
import shutil

# Constants
ORDERS_URL = "https://www.fanatical.com/en/orders"
ORDERS_API_URL = "https://www.fanatical.com/api/user/orders"
ENV_TOKEN = "FANATICAL_BEARER_TOKEN"
ORDER_DETAIL_API_URL = "https://www.fanatical.com/api/user/orders/{}"


def get_token(cli_token):
    env_token = os.environ.get(ENV_TOKEN)
    if cli_token:
        return cli_token
    if env_token:
        return env_token
    # Try to load from fanatical.TOKEN file
    try:
        with open("fanatical.TOKEN", "r", encoding="utf-8") as f:
            file_token = f.read().strip()
            if file_token:
                return file_token
    except Exception:
        pass
    print("Error: Bearer token must be provided via --token, $FANATICAL_BEARER_TOKEN, or fanatical.TOKEN file", file=sys.stderr)
    sys.exit(1)


def fetch_orders_page(token):
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (compatible; fanatical-order-listing/1.0)"
    }
    resp = requests.get(ORDERS_URL, headers=headers)
    if resp.status_code != 200:
        print(f"Error: Failed to fetch orders page (status {resp.status_code})", file=sys.stderr)
        sys.exit(2)
    return resp.text


def fetch_orders_api(token):
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (compatible; fanatical-order-listing/1.0)"
    }
    resp = requests.get(ORDERS_API_URL, headers=headers)
    if resp.status_code != 200:
        print(f"Error: Failed to fetch orders API (status {resp.status_code})", file=sys.stderr)
        sys.exit(2)
    return resp.json()


def fetch_order_detail(token, order_id):
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (compatible; fanatical-order-listing/1.0)"
    }
    url = ORDER_DETAIL_API_URL.format(order_id)
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"Warning: Failed to fetch details for order {order_id} (status {resp.status_code})", file=sys.stderr)
        return None
    return resp.json()


def extract_book_bundles_from_order_details(order_details):
    bundles = []
    for order in order_details:
        order_id = order.get('_id')
        order_date = order.get('date')
        items = order.get('items', [])
        # Track books by pickAndMix value if needed
        pick_and_mix_books = {}
        pick_and_mix_totals = {}
        for item in items:
            order_name = item.get('name')
            order_slug = item.get('slug')
            order_drm = item.get('drm')
            order_cover = item.get('cover')
            pick_and_mix = item.get('pickAndMix')
            payment_total = item.get('payment', {}).get('total', 0)
            books = []
            if 'bundles' in item and item['bundles']:
                for bundle in item['bundles']:
                    for book in bundle.get('games', []):
                        if book.get('type') in ('comic', 'book'):
                            book_entry = {
                                '_id': book.get('_id'),
                                'name': book.get('name'),
                                'cover': f"https://fanatical.imgix.net/product/original/{book.get('cover', '')}" if book.get('cover') else None,
                                'files': []
                            }
                            for download in book.get('downloads', []):
                                for file in download.get('files', []):
                                    file_entry = {
                                        '_id': file.get('_id'),
                                        'format': file.get('format'),
                                        'path': file.get('path'),
                                        'size_MB': round(file.get('size', 0) / 1024 / 1024, 2) if file.get('size') else None,
                                        'md5': file.get('md5'),
                                        'api_download': f"https://www.fanatical.com/api/user/download/{order_id}/{file.get('_id')}"
                                    }
                                    book_entry['files'].append(file_entry)
                            books.append(book_entry)
            else:
                if item.get('type') in ('comic', 'book'):
                    book_entry = {
                        '_id': item.get('_id'),
                        'name': item.get('name'),
                        'cover': f"https://fanatical.imgix.net/product/original/{item.get('cover', '')}" if item.get('cover') else None,
                        'files': []
                    }
                    for download in item.get('downloads', []):
                        for file in download.get('files', []):
                            file_entry = {
                                '_id': file.get('_id'),
                                'format': file.get('format'),
                                'path': file.get('path'),
                                'size_MB': round(file.get('size', 0) / 1024 / 1024, 2) if file.get('size') else None,
                                'md5': file.get('md5'),
                                'api_download': f"https://www.fanatical.com/api/user/download/{order_id}/{file.get('_id')}"
                            }
                            book_entry['files'].append(file_entry)
                    books.append(book_entry)
            if books:
                if pick_and_mix and item.get('type') != 'bundle':
                    pick_and_mix_books.setdefault(pick_and_mix, []).extend(books)
                    pick_and_mix_totals[pick_and_mix] = pick_and_mix_totals.get(pick_and_mix, 0) + payment_total
                else:
                    bundles.append({
                        '_id': order_id, 
                        'name': order_name, 
                        'slug': order_slug, 
                        'drm': order_drm, 
                        'cover': f"https://fanatical.imgix.net/product/original/{order_cover}" if order_cover else None,
                        'books': books,
                        'book_count': len(books),
                        'total_spent': payment_total,
                        'purchase_date': order_date,
                        'downloaded': False
                    })
        # Add pickAndMix bundles if needed
        for pick_and_mix, books in pick_and_mix_books.items():
            bundles.append({
                '_id': order_id, 
                'name': pick_and_mix, 
                'slug': pick_and_mix, 
                'drm': None, 
                'cover': None,  # pickAndMix bundles don't have a single cover
                'books': books,
                'book_count': len(books),
                'total_spent': pick_and_mix_totals[pick_and_mix],
                'purchase_date': order_date,
                'downloaded': False
            })
    return bundles


def load_existing_book_details(file_path):
    """Load existing book details from JSON file if it exists."""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except (json.JSONDecodeError, FileNotFoundError):
            pass
    return {"Book Bundles": 0, "All Bundles": 0, "bundles": []}

def merge_bundles(existing_bundles, new_bundles):
    """Merge new bundles with existing ones, preserving downloaded status."""
    existing_bundle_map = {bundle['_id']: bundle for bundle in existing_bundles}
    merged_bundles = []
    
    for new_bundle in new_bundles:
        bundle_id = new_bundle['_id']
        if bundle_id in existing_bundle_map:
            # Update existing bundle but preserve downloaded status
            existing_bundle = existing_bundle_map[bundle_id]
            new_bundle['downloaded'] = existing_bundle.get('downloaded', False)
            merged_bundles.append(new_bundle)
        else:
            # Add new bundle with default downloaded status
            new_bundle['downloaded'] = False
            merged_bundles.append(new_bundle)
    
    # Add any existing bundles that weren't in the new data
    for existing_bundle in existing_bundles:
        if existing_bundle['_id'] not in {b['_id'] for b in new_bundles}:
            merged_bundles.append(existing_bundle)
    
    return merged_bundles


def download_bundles(json_path, count, token):
    # Check if JSON file exists, if not create it
    if not os.path.exists(json_path):
        print(f"JSON file {json_path} does not exist. Please run with --books first to create it.")
        return
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    bundles = data.get('bundles', [])
    to_download = [b for b in bundles if not b.get('downloaded', False)][:count]
    if not to_download:
        print('No bundles to download.')
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (compatible; fanatical-order-listing/1.0)"
    }
    
    for bundle in to_download:
        bundle_dir = os.path.join('fanatical-downloads', bundle['slug'] or bundle['name'].replace(' ', '_'))
        os.makedirs(bundle_dir, exist_ok=True)
        for book in bundle.get('books', []):
            book_dir = os.path.join(bundle_dir, book['name'].replace(' ', '_'))
            os.makedirs(book_dir, exist_ok=True)
            for file in book.get('files', []):
                api_url = file.get('api_download')
                filename = file.get('path').split('.', 1)[-1] if file.get('path') else file.get('_id')
                dest_path = os.path.join(book_dir, filename)
                if os.path.exists(dest_path):
                    print(f"Already exists: {dest_path}")
                    continue
                
                # Fetch signed URL
                try:
                    resp = requests.get(api_url, headers=headers)
                    resp.raise_for_status()
                    signed_data = resp.json()
                    signed_url = signed_data.get('signedGetUrl')
                    
                    if not signed_url:
                        print(f"No signed URL found for {api_url}")
                        continue
                    
                    # Extract expiration date from signed URL
                    from urllib.parse import urlparse, parse_qs
                    parsed_url = urlparse(signed_url)
                    query_params = parse_qs(parsed_url.query)
                    expiration_date = query_params.get('X-Amz-Date', [None])[0]
                    
                    # Update file with signed URL and expiration date
                    file['signed_url'] = signed_url
                    file['expiration_date'] = expiration_date
                    
                    print(f"Downloading {signed_url} -> {dest_path}")
                    with requests.get(signed_url, stream=True) as r:
                        r.raise_for_status()
                        with open(dest_path, 'wb') as out:
                            shutil.copyfileobj(r.raw, out)
                            
                except Exception as e:
                    print(f"Failed to download {api_url}: {e}")
        bundle['downloaded'] = True
        print(f"Marked bundle '{bundle['name']}' as downloaded.")
    
    # Save updated JSON with expiration dates
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Updated {json_path} after downloading.")


def refresh_signed_urls(json_path, token):
    if not os.path.exists(json_path):
        print(f"JSON file {json_path} does not exist. Please run with --books first to create it.")
        return
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    bundles = data.get('bundles', [])
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (compatible; fanatical-order-listing/1.0)"
    }
    from urllib.parse import urlparse, parse_qs
    updated = 0
    for bundle in bundles:
        for book in bundle.get('books', []):
            for file in book.get('files', []):
                api_url = file.get('api_download')
                if not api_url:
                    continue
                try:
                    resp = requests.get(api_url, headers=headers)
                    resp.raise_for_status()
                    signed_data = resp.json()
                    signed_url = signed_data.get('signedGetUrl')
                    if not signed_url:
                        print(f"No signed URL found for {api_url}")
                        continue
                    parsed_url = urlparse(signed_url)
                    query_params = parse_qs(parsed_url.query)
                    expiration_date = query_params.get('X-Amz-Date', [None])[0]
                    file['signed_url'] = signed_url
                    file['expiration_date'] = expiration_date
                    updated += 1
                except Exception as e:
                    print(f"Failed to refresh {api_url}: {e}")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Refreshed signed URLs for {updated} files in {json_path}.")


def main():
    parser = argparse.ArgumentParser(description="List Fanatical orders as JSON.")
    parser.add_argument("--token", help="Bearer token for authentication (overrides $FANATICAL_BEARER_TOKEN)")
    parser.add_argument("--output", metavar="FILE", help="Save the JSON output to a file instead of printing to stdout")
    parser.add_argument("--details", action="store_true", help="Fetch full details for each order and save to fanatical-order-details.json")
    parser.add_argument("--books", action="store_true", help="Extract book details and save to fanatical-book-details.json in detailed_catalog.json format")
    parser.add_argument("--download", "-d", nargs="?", const=1, type=int, help="Download the first X not-yet-downloaded bundles (default 1)")
    parser.add_argument("--refresh", "-r", action="store_true", help="Refresh all signed URLs and expiration dates in fanatical-book-details.json")
    parser.add_argument("--save-html", metavar="FILE", help=argparse.SUPPRESS)  # Hide unused option
    args = parser.parse_args()

    if args.refresh:
        token = get_token(args.token)
        refresh_signed_urls("fanatical-book-details.json", token)
        return
    if args.download is not None:
        token = get_token(args.token)
        download_bundles("fanatical-book-details.json", args.download, token)
        return

    token = get_token(args.token)
    orders = fetch_orders_api(token)
    json_data = json.dumps(orders, indent=2, ensure_ascii=False)
    if args.details or args.books:
        details = []
        for order in orders:
            order_id = order.get("_id")
            if order_id:
                detail = fetch_order_detail(token, order_id)
                if detail:
                    details.append(detail)
        if args.details:
            with open("fanatical-order-details.json", "w", encoding="utf-8") as f:
                f.write(json.dumps(details, indent=2, ensure_ascii=False))
            print("Saved full order details to fanatical-order-details.json")
        if args.books:
            bundles = extract_book_bundles_from_order_details(details)
            
            # Load existing data and merge
            existing_data = load_existing_book_details("fanatical-book-details.json")
            merged_bundles = merge_bundles(existing_data.get('bundles', []), bundles)
            
            # Count book bundles (bundles with books of type comic or book)
            book_bundle_count = sum(1 for bundle in merged_bundles if any(book.get('type') in ('comic', 'book') for book in bundle.get('books', [])))
            
            output = {
                "Book Bundles": book_bundle_count,
                "All Bundles": len(merged_bundles),
                "bundles": merged_bundles
            }
            with open("fanatical-book-details.json", "w", encoding="utf-8") as f:
                f.write(json.dumps(output, indent=2, ensure_ascii=False))
            print("Updated book details in fanatical-book-details.json")
        return
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_data)
        print(f"Saved orders to {args.output}")
    else:
        print(json_data)

if __name__ == "__main__":
    main() 