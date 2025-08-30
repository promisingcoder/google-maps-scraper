#!/usr/bin/env python3
"""
Test script to demonstrate rate limiting functionality
"""

import time
from google_maps_scraper import GoogleMapsScraper

def test_rate_limiting():
    """Test the rate limiting functionality with multiple requests"""
    print("Testing rate limiting with multiple consecutive requests...")
    
    # Create scraper with short delays for testing
    scraper = GoogleMapsScraper(min_delay=1.0, max_delay=2.0, max_retries=2)
    
    # Test coordinates (Cairo)
    lat, lng, zoom = 30.0444, 31.2357, 13
    
    # Make multiple requests to test rate limiting
    queries = ["restaurants", "cafes", "hotels"]
    
    for i, query in enumerate(queries, 1):
        print(f"\n--- Request {i}: Searching for '{query}' ---")
        start_time = time.time()
        
        places = scraper.search_places(
            lat=lat, lng=lng, zoom=zoom, 
            query=query, max_results=1
        )
        
        end_time = time.time()
        print(f"Request {i} completed in {end_time - start_time:.2f} seconds")
        print(f"Found {len(places)} places")
        
        if places:
            print(f"First place: {places[0].get('name', 'Unknown')}")
    
    print(f"\nTotal requests made: {scraper.request_count}")
    print("Rate limiting test completed!")

if __name__ == "__main__":
    test_rate_limiting()