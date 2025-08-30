#!/usr/bin/env python3
"""
Google Maps Places Scraper

A Python scraper that extracts place data from Google Maps using the same API endpoints
that the web interface uses. Supports latitude, longitude, zoom level, query parameters,
and maximum results limiting.

Usage:
    python google_maps_scraper.py --lat 31.1276832 --lng 29.9064321 --zoom 13.1 --query "Restaurants" --max-results 20
"""

import argparse
import json
import re
import requests
import sys
import time
import random
import math
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import quote


class GoogleMapsScraper:
    def __init__(self, min_delay: float = 1.0, max_delay: float = 3.0, max_retries: int = 3):
        self.session = requests.Session()
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.last_request_time = 0
        self.request_count = 0
        self.setup_headers()
    
    def setup_headers(self):
        """Setup default headers to mimic a real browser request"""
        self.session.headers.update({
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'device-memory': '8',
            'downlink': '10',
            'priority': 'u=1, i',
            'referer': 'https://www.google.com/',
            'rtt': '150',
            'sec-ch-ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
            'x-browser-channel': 'stable',
            'x-browser-copyright': 'Copyright 2025 Google LLC. All rights reserved.',
            'x-browser-validation': 'XPdmRdCCj2OkELQ2uovjJFk6aKA=',
            'x-browser-year': '2025',
            'x-maps-diversion-context-bin': 'CAI='
        })
    
    def build_search_url(self, lat: float, lng: float, zoom: int, query: str, 
                        gl: str = 'eg', additional_params: Dict[str, str] = None) -> str:
        """Build the Google Maps search URL with the specified parameters"""
        
        # Calculate zoom distance based on zoom level (approximate)
        zoom_distance = 156543.03392 * 2 / (2 ** zoom)
        
        # Base URL and parameters
        base_url = "https://www.google.com/search"
        
        # Encode the query
        encoded_query = quote(query)
        
        # Build the pb parameter (protobuf-like parameter)
        # This is a complex parameter that contains map bounds, zoom, and other settings
        pb_parts = [
            "!4m8",
            "!1m3",
            f"!1d{zoom_distance}",
            f"!2d{lng}",
            f"!3d{lat}",
            "!3m2",
            "!1i415",
            "!2i608",
            f"!4f{zoom}",
            "!7i20",
            "!10b1",
            "!12m15",
            "!1m2",
            "!18b1",
            "!30b1",
            "!17m4",
            "!1e1",
            "!1e0",
            "!3e1",
            "!3e0",
            "!20m5",
            "!1e0",
            "!2e3",
            "!3b0",
            "!5e2",
            "!6b1",
            "!26b1",
            "!19m4",
            "!2m3",
            "!1i320",
            "!2i120",
            "!4i8",
            "!20m32",
            "!3m1",
            "!2i9",
            "!6m3",
            "!1m2",
            "!1i360",
            "!2i256",
            "!7m24",
            "!1m3",
            "!1e1",
            "!2b0",
            "!3e3",
            "!1m3",
            "!1e2",
            "!2b1",
            "!3e2",
            "!1m3",
            "!1e2",
            "!2b0",
            "!3e3",
            "!1m3",
            "!1e8",
            "!2b0",
            "!3e3",
            "!1m3",
            "!1e10",
            "!2b0",
            "!3e3",
            "!1m3",
            "!1e10",
            "!2b1",
            "!3e2",
            "!9b0"
        ]
        
        pb_param = "".join(pb_parts)
        
        # Build query parameters
        params = {
            'gl': gl,
            'tbm': 'map',
            'q': query,
            'pb': pb_param
        }
        
        # Add any additional parameters
        if additional_params:
            params.update(additional_params)
        
        # Build the full URL
        param_string = '&'.join([f"{k}={quote(str(v))}" for k, v in params.items()])
        return f"{base_url}?{param_string}"
    
    def safe_get(self, data: Any, path: List[Any], default: Any = None) -> Any:
        """Safely gets a value from a nested list/dict structure."""
        for key in path:
            try:
                data = data[key]
            except (IndexError, TypeError, KeyError):
                return default
        return data
    

    
    def clean_and_parse_json(self, raw_text: str) -> Optional[Any]:
        """Cleans the raw string and parses the main JSON-like structure."""
        # Remove the initial )]}' prefix if present
        if raw_text.startswith(")]}'\n"):
            raw_text = raw_text[5:]
        elif raw_text.startswith(")]}"):
            raw_text = raw_text[3:]
        
        # Find the start of the main JSON structure
        json_start = raw_text.find('[')
        if json_start == -1:
            return None
        
        # Slice the string from the start of the JSON
        json_str = raw_text[json_start:]
        
        # Attempt to parse it as JSON
        try:
            data = json.loads(json_str)
            return data
        except json.JSONDecodeError:
            # Fallback for formats that are not strict JSON but Python literals
            try:
                import ast
                return ast.literal_eval(json_str)
            except (ValueError, SyntaxError):
                return None
    

    

    
    def parse_restaurant_data(self, output_text: str) -> Dict[str, Any]:
        """Parses the raw text output to extract restaurant information into a structured JSON."""
        data = self.clean_and_parse_json(output_text)
        if not data:
            return {"error": "Failed to parse input data"}

        # Common base path for most data points
        base_path = [4, 0]
        
        # --- Basic Information ---
        full_name = self.safe_get(data, base_path + [21], "")
        rating = self.safe_get(data, base_path + [4, 7])
        reviews_count = self.safe_get(data, base_path + [4, 8])
        address = self.safe_get(data, base_path + [18])
        phone = self.safe_get(data, base_path + [178, 0, 0])
        plus_code = self.safe_get(data, base_path + [124, 1, 2])
        website = self.safe_get(data, base_path + [7, 0])

        # --- Price and Cuisine ---
        price_range_str = self.safe_get(data, base_path + [4, 2]) or self.safe_get(data, base_path + [4, 6])
        
        # Cuisine is usually the first category listed
        cuisine_list = self.safe_get(data, base_path + [22], [])
        cuisine = self.safe_get(cuisine_list, [0, 0]) if cuisine_list else None
        category = self.safe_get(cuisine_list, [0, 0])

        # --- Opening Hours ---
        opening_hours_raw = self.safe_get(data, base_path + [34, 4, 0], "")
        open_status, closes_at = None, None
        if opening_hours_raw and "⋅" in opening_hours_raw:
            parts = opening_hours_raw.split('⋅')
            open_status_str = parts[0].strip()
            open_now = "مفتوح" in open_status_str or "Open" in open_status_str
            closes_at = parts[1].strip()
        
        opening_hours = {
            "open": open_now if 'open_now' in locals() else None,
            "closes": closes_at.replace("يغلق ", "").replace("Closes ", "") if closes_at else None
        }

        # --- Services ---
        services = {}
        service_options = self.safe_get(data, base_path + [77], [])
        
        dine_in_present = any("dine_in" in str(s).lower() or "الجلوس" in str(s) for s in service_options)
        takeaway_present = any("takeout" in str(s).lower() or "سفري" in str(s) for s in service_options)
        delivery_present = any("delivery" in str(s).lower() or "توصيل" in str(s) for s in service_options)
        
        services = {
            "dine_in": dine_in_present,
            "takeaway": takeaway_present,
            "delivery": delivery_present
        }
        
        # --- Specific fields ---
        order_link = self.safe_get(data, base_path + [52, 0, 0, 1, 2, 1])

        review_highlights = {}
        review_text_for_highlights = self.safe_get(data, base_path + [138, 1, 0, 14, 0, 11, 4])
        if review_text_for_highlights:
            food_match = re.search(r'الأكل : (\d+/\d+)', review_text_for_highlights)
            place_match = re.search(r'المكان : (\d+/\d+)', review_text_for_highlights)
            atmosphere_match = re.search(r'الأجواء : (\d+/\d+)', review_text_for_highlights)
            if food_match: review_highlights["food_rating"] = food_match.group(1)
            if place_match: review_highlights["place_rating"] = place_match.group(1)
            if atmosphere_match: review_highlights["atmosphere_rating"] = atmosphere_match.group(1)
        
        # --- Constructing the final JSON based on what was found ---
        final_json = {
            "name": full_name,
            "rating": rating,
            "reviews_count": reviews_count,
            "price_range": price_range_str,
            "cuisine": cuisine,
            "category": category,
            "address": address,
            "plus_code": plus_code,
            "opening_hours": opening_hours,
            "services": services,
            "contact": {
                "phone": phone,
                "website": website,
                "order_link": order_link
            },
            "highlights": review_highlights if review_highlights else None
        }
        
        # Clean up None values and empty dicts for a cleaner output
        final_json = {k: v for k, v in final_json.items() if v is not None and v != {}}
        if "contact" in final_json:
            final_json["contact"] = {k: v for k, v in final_json["contact"].items() if v is not None}
            if not final_json["contact"]:
                del final_json["contact"]

        return final_json
    
    def extract_places_from_response(self, response_text: str) -> List[Dict[str, Any]]:
        """Extract places from the response text."""
        places = []
        
        # Parse the JSON data from response
        data = self.clean_and_parse_json(response_text)
        if not data:
            return places
        
        # Check if data[0][1] exists and contains place data
        if (isinstance(data, list) and len(data) > 0 and 
            data[0] is not None and isinstance(data[0], list) and
            len(data[0]) > 1 and data[0][1] is not None and isinstance(data[0][1], list)):
            
            # Iterate through each potential place in data[0][1]
            for i, place_data in enumerate(data[0][1]):
                if (isinstance(place_data, list) and len(place_data) > 14 and
                    place_data[14] is not None and isinstance(place_data[14], list)):
                    
                    # Parse place data directly using the correct structure
                      place_info = self.parse_place_from_structure(place_data)
                      if place_info and place_info.get('name'):
                          places.append(place_info)
        
        return places
    
    def parse_place_from_structure(self, place_data: List[Any]) -> Optional[Dict[str, Any]]:
        """Parse place information from the individual place data structure using only list indices."""
        try:
            place_info = {
                'name': None,
                'rating': None,
                'reviews_count': None,
                'address': None,
                'phone': None,
                'website': None,
                'price_range': None,
                'cuisine_type': None,
                'opening_hours': None,
                'services': [],
                'review_highlights': [],
                'coordinates': {'lat': None, 'lng': None}
            }
            
            # Extract place name and address from the structured data
            
            # Extract the place name - it's typically at place_data[14][11]
            name_found = False
            
            # First try place_data[14][11] which usually contains the place name
            if (len(place_data) > 14 and isinstance(place_data[14], list) and 
                len(place_data[14]) > 11 and isinstance(place_data[14][11], str) and 
                len(place_data[14][11]) > 0 and len(place_data[14][11]) < 100):
                
                # Check if it's not an ID or address component
                if not ('0x' in place_data[14][11] or ':' in place_data[14][11] or 
                        any(addr_word in place_data[14][11] for addr_word in ['شارع', 'طريق', 'محافظة', 'street', 'road'])):
                    place_info['name'] = place_data[14][11]
                    name_found = True
            
            # If not found at [11], look through other indices for a reasonable place name
            if not name_found and len(place_data) > 14 and isinstance(place_data[14], list):
                for i in range(len(place_data[14])):
                    if isinstance(place_data[14][i], str) and len(place_data[14][i]) > 0 and len(place_data[14][i]) < 100:
                        # Skip IDs, URLs, and address components
                        if (not ('0x' in place_data[14][i]) and 
                            not (':' in place_data[14][i] and len(place_data[14][i]) > 20) and 
                            not ('http' in place_data[14][i]) and 
                            not any(addr_word in place_data[14][i] for addr_word in ['شارع', 'طريق', 'محافظة', 'street', 'road', 'قسم']) and
                            not place_data[14][i].replace('_', '').replace('-', '').isalnum()):
                            
                            place_info['name'] = place_data[14][i]
                            name_found = True
                            break
            
            # Extract address components from place_data[14][2] (these are address parts)
            if (len(place_data) > 14 and 
                isinstance(place_data[14], list) and 
                len(place_data[14]) > 2 and 
                isinstance(place_data[14][2], list)):
                
                # All elements in place_data[14][2] are address components
                address_parts = [str(part) for part in place_data[14][2] if part]
                place_info['address'] = ', '.join(address_parts)
                print(f"Found address: {place_info['address']}")
            
            # Extract rating and review count from place_data[14][4]
            if (len(place_data) > 14 and isinstance(place_data[14], list) and 
                len(place_data[14]) > 4 and isinstance(place_data[14][4], list)):
                
                rating_data = place_data[14][4]
                
                # Rating is typically at index 7
                if (len(rating_data) > 7 and 
                    isinstance(rating_data[7], (int, float)) and 
                    0 <= rating_data[7] <= 5):
                    place_info['rating'] = rating_data[7]
                
                # Review count is typically at index 8
                if (len(rating_data) > 8 and 
                    isinstance(rating_data[8], (int, float))):
                    place_info['reviews_count'] = int(rating_data[8])
            
            # Extract phone numbers (can be multiple)
            phone_numbers = []
            try:
                if (len(place_data) > 14 and isinstance(place_data[14], list) and 
                    len(place_data[14]) > 178 and isinstance(place_data[14][178], list)):
                    
                    # Check if there are multiple phone number entries
                    for phone_entry in place_data[14][178]:
                        if isinstance(phone_entry, list) and len(phone_entry) > 0:
                            # Try to get formatted phone number first (with spaces)
                            phone = phone_entry[0] if phone_entry[0] else None
                            # If no formatted phone, try unformatted (without spaces)
                            if not phone and len(phone_entry) > 3:
                                phone = phone_entry[3]
                            
                            if phone and isinstance(phone, str) and phone.strip():
                                phone_numbers.append(phone.strip())
                    
                    # Set phone field - if multiple numbers, join with " | ", otherwise single number or None
                    if len(phone_numbers) == 1:
                        place_info['phone'] = phone_numbers[0]
                    elif len(phone_numbers) > 1:
                        place_info['phone'] = " | ".join(phone_numbers)
                    else:
                        place_info['phone'] = None
                        
            except (IndexError, TypeError):
                place_info['phone'] = None
            
            # Extract website
            website = None
            try:
                # Search through common website locations
                website_indices = [
                    [14, 7, 0],  # Primary website location
                    [14, 7, 1],  # Alternative location
                    [14, 7],     # Direct location
                    [14, 177],   # Another possible location
                    [14, 179],   # Adjacent to phone data
                ]
                
                for indices in website_indices:
                    try:
                        current_data = place_data
                        for idx in indices:
                            current_data = current_data[idx]
                        
                        if isinstance(current_data, str) and ('http' in current_data or 'www.' in current_data):
                            website = current_data
                            break
                        elif isinstance(current_data, list):
                            for item in current_data:
                                if isinstance(item, str) and ('http' in item or 'www.' in item):
                                    website = item
                                    break
                            if website:
                                break
                    except (IndexError, TypeError):
                        continue
                
                place_info['website'] = website
                
            except Exception as e:
                place_info['website'] = None
            
            # Extract price range
            price_range = None
            try:
                # Check primary and secondary price locations
                price_indices = [
                    [14, 4, 2],   # Primary location
                    [14, 4, 4],   # Secondary location (also contains price info)
                ]
                
                for indices in price_indices:
                    try:
                        current_data = place_data
                        for idx in indices:
                            current_data = current_data[idx]
                        
                        if isinstance(current_data, str) and current_data.strip():
                            # Check if it looks like price range (contains $ or price indicators)
                            if '$' in current_data or any(word in current_data.lower() for word in ['cheap', 'expensive', 'moderate', 'inexpensive']):
                                if not price_range:  # Use first valid price found
                                    price_range = current_data
                                    break
                        elif isinstance(current_data, (int, float)):
                            # Numeric price indicator (convert to dollar signs)
                            if 1 <= current_data <= 4:  # Typical price scale
                                price_symbols = '$' * int(current_data)
                                if not price_range:
                                    price_range = price_symbols
                                    break
                                    
                    except (IndexError, TypeError):
                        continue
                        
            except (IndexError, TypeError, KeyError):
                price_range = None
            
            place_info['price_range'] = price_range
            
            # Extract cuisine type
            cuisine_type = None
            try:
                # Cuisine type is typically found at [14, 13, 0]
                if len(place_data) > 14 and place_data[14] and len(place_data[14]) > 13 and place_data[14][13] and len(place_data[14][13]) > 0:
                    temp_cuisine = place_data[14][13][0]
                    if temp_cuisine and isinstance(temp_cuisine, str) and temp_cuisine.strip():
                        cuisine_type = temp_cuisine
            except (IndexError, TypeError, KeyError):
                cuisine_type = None
            
            place_info['cuisine_type'] = cuisine_type
            
            # Extract opening hours
            opening_hours = None
            try:
                current_data = place_data[14][34]
                if current_data and isinstance(current_data, list) and len(current_data) > 1:
                    # Look for structured hours data
                    hours_data = current_data[1] if len(current_data) > 1 else None
                    if isinstance(hours_data, list) and len(hours_data) > 0:
                        # Extract day/time pairs
                        hours_text = []
                        for day_info in hours_data:
                            if isinstance(day_info, list) and len(day_info) >= 2:
                                day = day_info[0] if day_info[0] else ''
                                times = day_info[1] if isinstance(day_info[1], list) and day_info[1] else []
                                if day and times:
                                    time_str = ', '.join(times) if isinstance(times, list) else str(times)
                                    hours_text.append(f"{day}: {time_str}")
                        
                        if hours_text:
                            opening_hours = '; '.join(hours_text)
            except (IndexError, TypeError):
                opening_hours = None
            
            place_info['opening_hours'] = opening_hours
            
            # Extract services (set to empty list as service data is not readily available)
            services = []
            
            place_info['services'] = services
            
            # Extract review highlights from index [14, 88]
            review_highlights = []
            try:
                if len(place_data[14]) > 88 and place_data[14][88] is not None:
                    data = place_data[14][88]
                    
                    if isinstance(data, list) and len(data) > 0:
                        # Extract all meaningful strings, excluding the place name
                        place_name = place_info.get('name', '').strip()
                        
                        for item in data:
                            if isinstance(item, str):
                                # Skip technical strings, addresses, and the place name itself
                                if (not item.startswith('SearchResult.TYPE_') and 
                                    not any(addr_word in item for addr_word in ['شارع', 'ميدان', 'محافظة', 'قسم']) and
                                    len(item.strip()) > 2 and
                                    item.strip() not in ['EG', 'None'] and
                                    item.strip() != place_name):
                                    review_highlights.append(item.strip())
                            elif isinstance(item, list):
                                # Handle nested lists - check for full review content
                                for subitem in item:
                                    if isinstance(subitem, str):
                                        if (not subitem.startswith('SearchResult.TYPE_') and 
                                            not any(addr_word in subitem for addr_word in ['شارع', 'ميدان', 'محافظة', 'قسم']) and
                                            len(subitem.strip()) > 2 and
                                            subitem.strip() not in ['EG', 'None'] and
                                            subitem.strip() != place_name):
                                            review_highlights.append(subitem.strip())
                                    elif isinstance(subitem, list):
                                        # Look deeper for potential full reviews
                                        for deep_item in subitem:
                                            if isinstance(deep_item, str) and len(deep_item.strip()) > 10:
                                                # Potential full review text
                                                if (not deep_item.startswith('SearchResult.TYPE_') and 
                                                    not any(addr_word in deep_item for addr_word in ['شارع', 'ميدان', 'محافظة', 'قسم']) and
                                                    deep_item.strip() != place_name):
                                                    review_highlights.append(deep_item.strip())
                        
                        # Remove duplicates while preserving order
                        seen = set()
                        unique_highlights = []
                        for highlight in review_highlights:
                            if highlight not in seen:
                                seen.add(highlight)
                                unique_highlights.append(highlight)
                        
                        review_highlights = unique_highlights
                        
            except Exception as e:
                print(f"  Review highlights extraction error for {place_info.get('name', 'Unknown')}: {e}")
                review_highlights = []
            
            place_info['review_highlights'] = review_highlights
            
            # Extract images from index [14, 72]
            images = []
            try:
                if len(place_data[14]) > 72 and place_data[14][72] is not None:
                    data = place_data[14][72]
                    if isinstance(data, list) and len(data) > 0:
                        # Access the nested structure: [14, 72][0][0][6][0]
                        first_item = data[0]
                        if isinstance(first_item, list) and len(first_item) > 0:
                            nested_item = first_item[0]
                            if isinstance(nested_item, list) and len(nested_item) > 6:
                                image_data = nested_item[6]
                                if isinstance(image_data, list) and len(image_data) > 0:
                                    img_url = image_data[0]
                                    if isinstance(img_url, str) and 'googleusercontent' in img_url:
                                        images.append(img_url)
            except Exception as e:
                print(f"  Images extraction error for {place_info.get('name', 'Unknown')}: {e}")
                images = []
            
            place_info['images'] = images
            
            # Extract coordinates (latitude and longitude)
            try:
                # Coordinates are found at place_data[14][9][2] for latitude and place_data[14][9][3] for longitude
                # Based on debugging, these are the confirmed indices for Google Maps API responses
                
                # Extract latitude
                lat_value = self.safe_get(place_data, [14, 9, 2])
                if isinstance(lat_value, (int, float)) and -90 <= lat_value <= 90:
                    place_info['coordinates']['lat'] = lat_value
                
                # Extract longitude  
                lng_value = self.safe_get(place_data, [14, 9, 3])
                if isinstance(lng_value, (int, float)) and -180 <= lng_value <= 180:
                    place_info['coordinates']['lng'] = lng_value
                
                # Fallback: try alternative coordinate locations if primary ones fail
                if place_info['coordinates']['lat'] is None or place_info['coordinates']['lng'] is None:
                    # Try alternative locations
                    for lat_indices in [[14, 1, 2], [14, 0, 2]]:
                        if place_info['coordinates']['lat'] is None:
                            lat_value = self.safe_get(place_data, lat_indices)
                            if isinstance(lat_value, (int, float)) and -90 <= lat_value <= 90:
                                place_info['coordinates']['lat'] = lat_value
                                break
                    
                    for lng_indices in [[14, 1, 3], [14, 0, 3]]:
                        if place_info['coordinates']['lng'] is None:
                            lng_value = self.safe_get(place_data, lng_indices)
                            if isinstance(lng_value, (int, float)) and -180 <= lng_value <= 180:
                                place_info['coordinates']['lng'] = lng_value
                                break
                
            except Exception as e:
                # Silently handle coordinate extraction errors
                place_info['coordinates'] = {'lat': None, 'lng': None}
            
            return place_info if place_info.get('name') else None
            
        except (IndexError, TypeError) as e:
            print(f"Error parsing place data: {e}")
            return None
    
    def apply_rate_limiting(self):
        """Apply rate limiting between requests"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        # Calculate delay based on request count (progressive backoff)
        base_delay = random.uniform(self.min_delay, self.max_delay)
        
        # Add progressive delay for frequent requests
        if self.request_count > 10:
            base_delay *= 1.5
        elif self.request_count > 20:
            base_delay *= 2.0
        
        # Ensure minimum delay between requests
        if time_since_last_request < base_delay:
            sleep_time = base_delay - time_since_last_request
            print(f"Rate limiting: waiting {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    def make_request_with_retry(self, url: str) -> requests.Response:
        """Make a request with retry logic and rate limiting"""
        for attempt in range(self.max_retries):
            try:
                # Apply rate limiting before each request
                self.apply_rate_limiting()
                
                print(f"Making request (attempt {attempt + 1}/{self.max_retries})...")
                response = self.session.get(url, timeout=30)
                
                # Check for rate limiting responses
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    print(f"Rate limited by server. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                print(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    # Exponential backoff for retries
                    wait_time = (2 ** attempt) * random.uniform(1, 3)
                    print(f"Retrying in {wait_time:.2f} seconds...")
                    time.sleep(wait_time)
                else:
                    raise
        
        raise requests.RequestException(f"Failed after {self.max_retries} attempts")
    
    def lat_lng_to_tile(self, lat: float, lng: float, zoom: int) -> Tuple[int, int]:
        """Convert latitude/longitude to tile coordinates using Web Mercator projection"""
        lat_rad = math.radians(lat)
        n = 2.0 ** zoom
        x = int((lng + 180.0) / 360.0 * n)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return x, y
    
    def tile_to_lat_lng(self, x: int, y: int, zoom: int) -> Tuple[float, float]:
        """Convert tile coordinates to latitude/longitude"""
        n = 2.0 ** zoom
        lng = x / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
        lat = math.degrees(lat_rad)
        return lat, lng
    
    def calculate_tile_radius(self, center_lat: float, center_lng: float, zoom: int, radius_km: float) -> int:
        """Calculate how many tiles to search in each direction for a given radius in kilometers
        Uses TomTom's tile grid calculations: circumference of earth / 2^zoom level
        """
        # TomTom formula: meters per tile side = 40,075,017 / 2^zoom
        earth_circumference_meters = 40075017
        meters_per_tile_side = earth_circumference_meters / (2 ** zoom)
        
        # Convert radius from km to meters
        radius_meters = radius_km * 1000
        
        # Calculate how many tiles needed to cover the radius
        tiles_needed = math.ceil(radius_meters / meters_per_tile_side)
        
        # Ensure minimum of 1 tile
        return max(1, tiles_needed)
    
    def get_zoom_levels(self, radius_km: float, min_zoom: int = 10) -> List[int]:
        """Get zoom levels for searching based on radius and minimum zoom preference
        """
        # Test zoom levels from min_zoom to 21 (respecting user's minimum zoom preference)
        start_zoom = max(10, min_zoom)  # Ensure we don't go below zoom 10
        zoom_levels = list(range(start_zoom, 22))
        
        return zoom_levels
    
    def calculate_tile_coverage_stats(self, center_lat: float, center_lng: float, zoom: int, radius_km: float) -> Dict[str, Any]:
        """Calculate detailed tile coverage statistics using TomTom's formulas"""
        earth_circumference_meters = 40075017
        meters_per_tile_side = earth_circumference_meters / (2 ** zoom)
        
        # Calculate tile radius
        tile_radius = self.calculate_tile_radius(center_lat, center_lng, zoom, radius_km)
        
        # Total tiles in the search area
        total_tiles = (2 * tile_radius + 1) ** 2
        
        # Coverage area in square kilometers
        tile_side_km = meters_per_tile_side / 1000
        coverage_area_km2 = total_tiles * (tile_side_km ** 2)
        
        return {
            'zoom_level': zoom,
            'meters_per_tile_side': meters_per_tile_side,
            'tile_radius': tile_radius,
            'total_tiles': total_tiles,
            'tile_side_km': tile_side_km,
            'coverage_area_km2': coverage_area_km2,
            'search_radius_km': radius_km
        }
    
    def generate_tile_coordinates(self, center_lat: float, center_lng: float, zoom: int, radius_km: float = 10) -> List[Tuple[int, int, float, float]]:
        """Generate tile coordinates and their center lat/lng for systematic searching"""
        center_x, center_y = self.lat_lng_to_tile(center_lat, center_lng, zoom)
        tile_radius = self.calculate_tile_radius(center_lat, center_lng, zoom, radius_km)
        
        tiles = []
        for dx in range(-tile_radius, tile_radius + 1):
            for dy in range(-tile_radius, tile_radius + 1):
                tile_x = center_x + dx
                tile_y = center_y + dy
                
                # Convert tile back to lat/lng for the search
                tile_lat, tile_lng = self.tile_to_lat_lng(tile_x, tile_y, zoom)
                tiles.append((tile_x, tile_y, tile_lat, tile_lng))
        
        return tiles
    
    def search_places(self, lat: float, lng: float, zoom: int, query: str, 
                     max_results: int = 20, gl: str = 'eg', 
                     additional_params: Dict[str, str] = None, 
                     search_radius_km: float = 10) -> List[Dict[str, Any]]:
        """Search for places using enhanced tile-based systematic searching with multi-zoom level support"""
        
        all_places = []
        unique_places = set()  # Track unique places by name and address
        
        # If max_results is greater than 20, use advanced multi-zoom tile-based searching
        if max_results > 20:
            print(f"Large result set requested ({max_results}). Using advanced multi-zoom tile-based searching...")
            
            # Get zoom levels for comprehensive coverage (respecting minimum zoom)
            optimal_zooms = self.get_zoom_levels(search_radius_km, zoom)
            print(f"Zoom levels for {search_radius_km}km radius, min zoom {zoom}: {optimal_zooms}")
            
            # Search at each optimal zoom level with adaptive skipping
            zoom_idx = 0
            while zoom_idx < len(optimal_zooms):
                if len(all_places) >= max_results:
                    break
                
                current_zoom = optimal_zooms[zoom_idx]
                print(f"\n=== ZOOM LEVEL {current_zoom} ({zoom_idx + 1}/{len(optimal_zooms)}) ===")
                
                # Track unique places before this zoom level
                places_before_zoom = len(all_places)
                
                # Calculate coverage statistics
                coverage_stats = self.calculate_tile_coverage_stats(lat, lng, current_zoom, search_radius_km)
                print(f"Coverage: {coverage_stats['total_tiles']} tiles, {coverage_stats['coverage_area_km2']:.2f} km², {coverage_stats['meters_per_tile_side']:.0f}m per tile")
                
                # Generate tile coordinates for this zoom level
                tiles = self.generate_tile_coordinates(lat, lng, current_zoom, search_radius_km)
                
                # No artificial tile limiting - search all tiles until max_results is reached
                # Only prioritize tiles by distance from center for systematic coverage
                center_x, center_y = self.lat_lng_to_tile(lat, lng, current_zoom)
                tiles.sort(key=lambda t: abs(t[0] - center_x) + abs(t[1] - center_y))
                
                remaining_results = max_results - len(all_places)
                print(f"Searching all {len(tiles)} tiles at zoom {current_zoom} (need {remaining_results} more results)")
                
                # Search each tile systematically
                for i, (tile_x, tile_y, tile_lat, tile_lng) in enumerate(tiles):
                    if len(all_places) >= max_results:
                        break
                        
                    print(f"Tile {i+1}/{len(tiles)}: ({tile_x}, {tile_y}) -> ({tile_lat:.6f}, {tile_lng:.6f})")
                    
                    try:
                        url = self.build_search_url(tile_lat, tile_lng, current_zoom, query, gl, additional_params)
                        response = self.make_request_with_retry(url)
                        
                        # Extract places from the response
                        places = self.extract_places_from_response(response.text)
                        
                        # Add unique places
                        new_places_count = 0
                        for place in places:
                            if place and place.get('name'):
                                # Create unique identifier
                                place_id = f"{place['name']}_{place.get('address', '')}"
                                if place_id not in unique_places:
                                    unique_places.add(place_id)
                                    all_places.append(place)
                                    new_places_count += 1
                                    
                                    if len(all_places) >= max_results:
                                        break
                        
                        print(f"Found {len(places)} places, {new_places_count} new unique. Total: {len(all_places)}")
                        
                    except Exception as e:
                        print(f"Error searching tile ({tile_x}, {tile_y}): {e}")
                        continue
                    
                    # Rate limiting between tile searches
                    if i < len(tiles) - 1 or zoom_idx < len(optimal_zooms) - 1:
                        delay = random.uniform(self.min_delay, self.max_delay)
                        time.sleep(delay)
                
                # Check if this zoom level found any new unique places
                new_unique_at_zoom = len(all_places) - places_before_zoom
                print(f"Zoom {current_zoom} complete: {len(all_places)} total unique places found ({new_unique_at_zoom} new at this zoom)")
                
                # Adaptive zoom level skipping when no unique places found
                if new_unique_at_zoom == 0:
                    remaining_zooms = len(optimal_zooms) - zoom_idx - 1
                    skip_count = min(5, remaining_zooms)  # Skip up to 5 levels or remaining levels
                    
                    if skip_count > 0:
                        print(f"⚠️  No new unique places found at zoom {current_zoom}. Skipping {skip_count} zoom levels...")
                        skipped_zooms = optimal_zooms[zoom_idx + 1:zoom_idx + 1 + skip_count]
                        print(f"Skipped zoom levels: {skipped_zooms}")
                        zoom_idx += skip_count + 1  # Skip ahead
                    else:
                        zoom_idx += 1
                else:
                    zoom_idx += 1
            
        else:
            # Single search for smaller result sets
            url = self.build_search_url(lat, lng, zoom, query, gl, additional_params)
            
            try:
                print(f"Searching for '{query}' at coordinates ({lat}, {lng}) with zoom {zoom}...")
                response = self.make_request_with_retry(url)
                
                # Extract places from the response
                places = self.extract_places_from_response(response.text)
                all_places = places
                
            except requests.RequestException as e:
                print(f"Error making request: {e}")
                return []
            except Exception as e:
                print(f"Error processing response: {e}")
                return []
        
        # Limit results to max_results
        if max_results and len(all_places) > max_results:
            all_places = all_places[:max_results]
        
        print(f"\nFinal result: Found {len(all_places)} unique places using tile-based search")
        return all_places


def main():
    parser = argparse.ArgumentParser(
        description='Google Maps Places Scraper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python google_maps_scraper.py --lat 31.1276832 --lng 29.9064321 --zoom 13.1 --query "Restaurants" --max-results 20
  python google_maps_scraper.py --lat 40.7128 --lng -74.0060 --zoom 12 --query "Coffee shops" --max-results 10 --gl us
  python google_maps_scraper.py --lat 31.1276832 --lng 29.9064321 --zoom 13.1 --query "Hotels" --min-delay 2.0 --max-delay 5.0 --max-retries 5
        """
    )
    
    parser.add_argument('--lat', type=float, required=True,
                       help='Latitude coordinate for the search center')
    parser.add_argument('--lng', type=float, required=True,
                       help='Longitude coordinate for the search center')
    parser.add_argument('--zoom', type=int, required=True,
                       help='Base zoom level (e.g., 13 for city level). For large searches, multiple zoom levels will be used automatically')
    parser.add_argument('--zoom-levels', type=str, 
                       help='Comma-separated list of specific zoom levels to use (e.g., "12,13,14"). Overrides automatic zoom selection')
    parser.add_argument('--query', type=str, required=True,
                       help='Search query (e.g., "Restaurants", "Coffee shops")')
    parser.add_argument('--max-results', type=int, default=20,
                       help='Maximum number of results to return (default: 20)')
    parser.add_argument('--gl', type=str, default='eg',
                       help='Google country code (default: eg for Egypt)')
    parser.add_argument('--output', type=str,
                       help='Output file path (JSON format). If not specified, prints to stdout')
    parser.add_argument('--min-delay', type=float, default=1.0,
                       help='Minimum delay between requests in seconds (default: 1.0)')
    parser.add_argument('--max-delay', type=float, default=3.0,
                       help='Maximum delay between requests in seconds (default: 3.0)')
    parser.add_argument('--max-retries', type=int, default=3,
                       help='Maximum number of retry attempts for failed requests (default: 3)')
    parser.add_argument('--search-radius', type=float, default=10.0,
                       help='Search radius in kilometers for tile-based searching (default: 10.0)')
    
    args = parser.parse_args()
    
    # Create scraper instance with rate limiting
    scraper = GoogleMapsScraper(
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        max_retries=args.max_retries
    )
    
    # Handle custom zoom levels if specified
    if args.zoom_levels:
        try:
            custom_zooms = [int(z.strip()) for z in args.zoom_levels.split(',')]
            print(f"Using custom zoom levels: {custom_zooms}")
            # Override the get_optimal_zoom_levels method temporarily
            original_method = scraper.get_optimal_zoom_levels
            scraper.get_optimal_zoom_levels = lambda radius, max_res: custom_zooms
        except ValueError:
            print(f"Invalid zoom levels format: {args.zoom_levels}. Using automatic selection.")
    
    # Search for places
    places = scraper.search_places(
        lat=args.lat,
        lng=args.lng,
        zoom=args.zoom,
        query=args.query,
        max_results=args.max_results,
        gl=args.gl,
        search_radius_km=args.search_radius
    )
    
    # Restore original method if it was overridden
    if args.zoom_levels:
        try:
            scraper.get_optimal_zoom_levels = original_method
        except:
            pass
    
    # Prepare output
    output_data = {
        "search_parameters": {
            "lat": args.lat,
            "lng": args.lng,
            "zoom": args.zoom,
            "query": args.query,
            "max_results": args.max_results,
            "gl": args.gl
        },
        "results_count": len(places),
        "places": places
    }
    
    # Output results
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"Results saved to {args.output}")
    else:
        print(json.dumps(output_data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()