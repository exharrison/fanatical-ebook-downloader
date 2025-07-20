# Fanatical Ebook Downloader

A Python script to list and download your ebook purchases from [Fanatical](https://www.fanatical.com/). This tool helps you organize and download your digital book collection from Fanatical's platform.

## Features

- **Order Listing**: Fetch and display all your Fanatical orders as JSON
- **Book Extraction**: Extract book-specific details from your orders
- **Download Management**: Download ebooks and comics with proper organization
- **Signed URL Management**: Handle temporary download URLs with automatic refresh
- **Progress Tracking**: Track which bundles have been downloaded
- **Flexible Authentication**: Support for environment variables, command line tokens, or token files

## Requirements

- Python 3.6+
- Required Python packages:
  - `requests`
  - `beautifulsoup4`

## Installation

1. Clone or download this repository
2. Install required dependencies:

```bash
pip install requests beautifulsoup4
```

## Authentication

You need a Bearer token from Fanatical to use this script. The script supports three ways to provide the token:

1. **Environment Variable**: Set `FANATICAL_BEARER_TOKEN`
2. **Command Line**: Use the `--token` argument
3. **Token File**: Create a `fanatical.TOKEN` file with your token

### Getting Your Bearer Token

1. Log into your Fanatical account in a web browser
2. Open Developer Tools (F12)
3. Go to the Network tab
4. Navigate to your orders page
5. Look for API requests and find the `Authorization: Bearer <token>` header
6. Copy the token value

## Usage

### Basic Order Listing

List all your orders as JSON:

```bash
python fanatical-order-listing.py
```

Save orders to a file:

```bash
python fanatical-order-listing.py --output my-orders.json
```

### Extract Book Details

Extract book-specific information and save to `fanatical-book-details.json`:

```bash
python fanatical-order-listing.py --books
```

This creates a structured JSON file with:
- Book bundle information
- Individual book details
- Download URLs and file information
- File sizes and formats

### Download Ebooks

Download the first undownloaded bundle:

```bash
python fanatical-order-listing.py --download
```

Download multiple bundles:

```bash
python fanatical-order-listing.py --download 5
```

### Refresh Download URLs

Fanatical's download URLs expire. Refresh them:

```bash
python fanatical-order-listing.py --refresh
```

### Get Detailed Order Information

Fetch complete order details and save to `fanatical-order-details.json`:

```bash
python fanatical-order-listing.py --details
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `--token TOKEN` | Bearer token for authentication |
| `--output FILE` | Save JSON output to specified file |
| `--details` | Fetch full order details |
| `--books` | Extract book details and save to `fanatical-book-details.json` |
| `--download [COUNT]` | Download first N undownloaded bundles (default: 1) |
| `--refresh` | Refresh signed URLs in book details file |

## File Structure

The script creates several files:

- `fanatical-order-details.json`: Complete order information
- `fanatical-book-details.json`: Book-specific details with download tracking
- `fanatical-downloads/`: Directory containing downloaded ebooks organized by bundle

### Download Organization

Ebooks are organized as:
```
fanatical-downloads/
├── bundle_name/
│   ├── book_title/
│   │   ├── book_file_1.pdf
│   │   └── book_file_2.epub
│   └── another_book/
│       └── book_file.pdf
```

## JSON Output Format

### Book Details Structure

```json
{
  "Book Bundles": 5,
  "All Bundles": 10,
  "bundles": [
    {
      "_id": "order_id",
      "name": "Bundle Name",
      "slug": "bundle-slug",
      "drm": "DRM type",
      "cover": "cover_image_url",
      "books": [
        {
          "_id": "book_id",
          "name": "Book Title",
          "cover": "book_cover_url",
          "files": [
            {
              "_id": "file_id",
              "format": "pdf",
              "path": "file_path",
              "size_MB": 15.5,
              "md5": "file_hash",
              "api_download": "download_api_url",
              "signed_url": "temporary_download_url",
              "expiration_date": "expiration_timestamp"
            }
          ]
        }
      ],
      "book_count": 3,
      "total_spent": 9.99,
      "purchase_date": "2023-01-01T00:00:00Z",
      "downloaded": false
    }
  ]
}
```

## Features

### Download Tracking

The script tracks which bundles have been downloaded and won't re-download them unless you manually reset the `downloaded` flag.

### Signed URL Management

Fanatical uses temporary signed URLs for downloads. The script:
- Fetches fresh signed URLs when downloading
- Stores expiration dates
- Provides a refresh command to update expired URLs

### Pick and Mix Support

Handles Fanatical's "Pick and Mix" bundles by grouping individual book selections into logical bundles.

### Error Handling

- Graceful handling of network errors
- Continues processing even if individual downloads fail
- Preserves existing downloads when re-running

## Troubleshooting

### Common Issues

1. **Authentication Error**: Ensure your Bearer token is valid and not expired
2. **Download Failures**: Try refreshing signed URLs with `--refresh`
3. **Missing Files**: Check that the JSON file exists before downloading
4. **Network Errors**: Verify your internet connection and try again

### Token Expiration

If you get authentication errors, your Bearer token may have expired. Get a new token from the browser and update your authentication method.

## Security Notes

- Keep your Bearer token secure and don't share it
- The token file (`fanatical.TOKEN`) should have restricted permissions
- Consider using environment variables for production use

## License

This script is provided as-is for personal use. Please respect Fanatical's terms of service when using this tool.

## Contributing

Feel free to submit issues or pull requests for improvements. Please ensure any changes maintain compatibility with Fanatical's API. 

## Discord Notifications

This script can send notifications to a Discord channel via webhook for:
- **New bundle detected** (when running with `--books`)
- **Bundle successfully downloaded** (when running with `--download`)
- **Script errors** (if the script fails or exits with an error)

### How to Provide the Webhook URL

You can provide your Discord webhook URL in three ways:
1. **Command Line Argument:** `--discord-webhook <URL>`
2. **Environment Variable:** `DISCORD_WEBHOOK_URL`
3. **Hardcoded in your shell script** (e.g., in `nightly-update.sh`)

### Example Notification
- **New Bundle:**
  > New Fanatical Bundle: [Bundle Name]
  > Books: 10
  > Spent: $7.99
- **Bundle Downloaded:**
  > Bundle Downloaded: [Bundle Name]
  > Books: 10
  > Spent: $7.99
- **Error:**
  > Fanatical Ebook Downloader: Error
  > An error occurred: ...

## Price Formatting

- Prices in notifications are now always shown as dollars and cents (e.g., `$7.99`).
- Internally, prices are stored as cents (e.g., `799` for $7.99). 