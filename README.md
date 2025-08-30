# Google Maps Scraper

A powerful Python tool for scraping place data from Google Maps using advanced multi-zoom tile-based searching.

## Features

- **Multi-zoom tile-based searching** for comprehensive coverage
- **Configurable search parameters** (location, radius, zoom levels)
- **Rate limiting** to avoid being blocked
- **Duplicate detection** to ensure unique results
- **Detailed place information** including ratings, reviews, contact info
- **JSON output** for easy data processing
- **Arabic language support** for Middle Eastern locations

## Installation

1. Clone this repository:
```bash
git clone https://github.com/promisingcoder/google-maps-scraper.git
cd google-maps-scraper
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python google_maps_scraper.py --lat 31.1454645 --lng 30.1157236 --query "restaurants" --max-results 50 --search-radius 10
```

### Advanced Usage

```bash
python google_maps_scraper.py \
  --lat 31.1454645 \
  --lng 30.1157236 \
  --zoom 14 \
  --query "مطعم" \
  --max-results 100 \
  --search-radius 15 \
  --output results.json \
  --min-delay 0.5 \
  --max-delay 1.5 \
  --gl eg
```

### Parameters

| Parameter | Description | Default |
|-----------|-------------|----------|
| `--lat` | Latitude coordinate | Required |
| `--lng` | Longitude coordinate | Required |
| `--query` | Search query (e.g., "restaurants", "مطعم") | Required |
| `--max-results` | Maximum number of results to return | 20 |
| `--zoom` | Minimum zoom level for searching | 15 |
| `--search-radius` | Search radius in kilometers | 10 |
| `--output` | Output JSON file path | stdout |
| `--min-delay` | Minimum delay between requests (seconds) | 1.0 |
| `--max-delay` | Maximum delay between requests (seconds) | 3.0 |
| `--gl` | Google country code (e.g., 'eg' for Egypt) | 'eg' |
| `--zoom-levels` | Custom zoom levels (comma-separated) | Auto |

## How It Works

### Search Strategies

1. **Single Search** (≤20 results): Simple single API call
2. **Multi-zoom Tile-based Search** (>20 results): Advanced systematic searching
   - Generates tiles covering the search area
   - Searches multiple zoom levels (14-18)
   - Prioritizes tiles by distance from center
   - Continues until target results reached

### Data Extraction

The scraper extracts comprehensive place information:

- **Basic Info**: Name, address, rating, review count
- **Contact**: Phone numbers, website
- **Details**: Price range, cuisine type, opening hours
- **Additional**: Services, review highlights, images

## Output Format

```json
{
  "search_parameters": {
    "lat": 31.1454645,
    "lng": 30.1157236,
    "zoom": 14,
    "query": "restaurants",
    "max_results": 50,
    "gl": "eg"
  },
  "results_count": 45,
  "places": [
    {
      "name": "Restaurant Name",
      "rating": 4.5,
      "reviews_count": 123,
      "address": "Street Address, City",
      "phone": "+20123456789",
      "website": "https://example.com",
      "price_range": "$$",
      "cuisine_type": "Italian",
      "opening_hours": "Mon-Sun: 10:00-22:00",
      "services": ["Delivery", "Takeout"],
      "review_highlights": ["Great food", "Excellent service"],
      "images": ["https://image-url.com"]
    }
  ]
}
```

## Rate Limiting

The scraper includes built-in rate limiting to avoid being blocked:

- Configurable delays between requests (0.5-3.0 seconds)
- Automatic retry mechanism with exponential backoff
- Request headers that mimic real browser behavior

## Examples

### Search for Restaurants in Cairo
```bash
python google_maps_scraper.py --lat 30.0444 --lng 31.2357 --query "restaurants" --max-results 100 --output cairo_restaurants.json
```

### Search for Hotels in Alexandria
```bash
python google_maps_scraper.py --lat 31.2001 --lng 29.9187 --query "hotels" --max-results 50 --search-radius 5 --output alexandria_hotels.json
```

### Search with Arabic Query
```bash
python google_maps_scraper.py --lat 31.1454645 --lng 30.1157236 --query "مطعم" --max-results 75 --output arabic_restaurants.json
```

## Troubleshooting

### Common Issues

1. **Low Results**: Increase search radius or lower minimum zoom level
2. **Rate Limiting**: Increase delays between requests
3. **No Results**: Check coordinates and query spelling
4. **Encoding Issues**: Ensure UTF-8 encoding for Arabic text

### Debug Mode

The scraper provides detailed logging during execution:

```
Large result set requested (100). Using advanced multi-zoom tile-based searching...
Zoom levels for 0.5km radius, min zoom 14: [14, 15, 16, 17, 18]
=== ZOOM LEVEL 14 (1/5) ===
Generating tiles for zoom 14, radius 0.5km...
Tile 1/4: (8543, 5684) -> (31.145123, 30.115456)
Found 15 places, 12 new unique. Total: 12
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is for educational purposes only. Please respect Google's Terms of Service and use responsibly.

## Disclaimer

This tool is for educational and research purposes only. Users are responsible for complying with Google's Terms of Service and applicable laws. The authors are not responsible for any misuse of this tool.