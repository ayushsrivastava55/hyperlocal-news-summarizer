"""
Geo-tagging Module
Extracts and geocodes location information from articles
"""

import logging
from typing import Dict, List, Optional, Tuple
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import re
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeoTagger:
    """Extracts and geocodes locations from news articles"""
    
    def __init__(self):
        self.geolocator = Nominatim(user_agent="hyperlocal_news_summarizer")
        self.common_cities = {
            'nagpur': (21.1458, 79.0882),
            'mumbai': (19.0760, 72.8777),
            'delhi': (28.6139, 77.2090),
            'bangalore': (12.9716, 77.5946),
            'pune': (18.5204, 73.8567),
            'hyderabad': (17.3850, 78.4867),
            'chennai': (13.0827, 80.2707),
            'kolkata': (22.5726, 88.3639)
        }
    
    def extract_location_keywords(self, text: str) -> List[str]:
        """
        Extract potential location names from text
        
        Args:
            text: Input text
            
        Returns:
            List of potential location names
        """
        locations = []
        
        # Common Indian city patterns
        city_patterns = [
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Municipal|Corporation|MC|Nagar|City|District)',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*(?:Maharashtra|Karnataka|Tamil Nadu|Gujarat|etc)',
            r'\bin\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'\bat\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]
        
        for pattern in city_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            locations.extend(matches)
        
        # Extract capitalized words that might be locations
        words = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', text)
        # Filter out common non-location words
        non_locations = {'The', 'This', 'That', 'These', 'Those', 'A', 'An', 'And', 'Or', 'But'}
        potential_locations = [w for w in words if w not in non_locations and len(w) > 3]
        locations.extend(potential_locations[:5])  # Limit to top 5
        
        return list(set(locations))
    
    def geocode_location(self, location_name: str, retries: int = 3) -> Optional[Dict]:
        """
        Geocode a location name to coordinates
        
        Args:
            location_name: Name of the location
            retries: Number of retry attempts
            
        Returns:
            Dictionary with location info and coordinates, or None
        """
        # Check common cities first
        location_lower = location_name.lower().strip()
        if location_lower in self.common_cities:
            lat, lon = self.common_cities[location_lower]
            return {
                'name': location_name,
                'latitude': lat,
                'longitude': lon,
                'formatted_address': f"{location_name}, India",
                'confidence': 'high'
            }
        
        # Try geocoding
        for attempt in range(retries):
            try:
                time.sleep(1)  # Rate limiting
                location = self.geolocator.geocode(
                    f"{location_name}, India",
                    timeout=10
                )
                
                if location:
                    return {
                        'name': location_name,
                        'latitude': location.latitude,
                        'longitude': location.longitude,
                        'formatted_address': location.address,
                        'confidence': 'medium'
                    }
                    
            except (GeocoderTimedOut, GeocoderServiceError) as e:
                if attempt == retries - 1:
                    logger.error(f"Geocoding failed for {location_name}: {str(e)}")
                else:
                    time.sleep(2 ** attempt)  # Exponential backoff
            except Exception as e:
                logger.error(f"Error geocoding {location_name}: {str(e)}")
                break
        
        return None
    
    def tag_article(self, article: Dict, entities: Optional[Dict] = None, fast: bool = False) -> Dict:
        """
        Geo-tag an article with location information
        
        Args:
            article: Article dictionary
            entities: Optional pre-extracted entities (from NER)
            
        Returns:
            Article with geo-tagging information added
        """
        tagged_article = article.copy()
        
        # Get text for location extraction
        text = f"{article.get('title', '')} {article.get('description', '')}"
        
        # Extract locations from entities if available
        locations = []
        if entities and 'named_entities' in entities:
            ner_entities = entities['named_entities']
            locations.extend(ner_entities.get('GPE', []))
            locations.extend(ner_entities.get('LOC', []))
        
        # Also extract from text directly
        text_locations = self.extract_location_keywords(text)
        locations.extend(text_locations)
        
        # Remove duplicates
        locations = list(dict.fromkeys(locations))
        
        # Geocode locations
        geo_tags = []
        primary_location = None
        
        for loc in locations[:3]:  # Limit to top 3 locations
            if fast:
                # In fast mode, only resolve from common cities (no network)
                geo_info = None
                loc_l = loc.lower().strip()
                if loc_l in self.common_cities:
                    lat, lon = self.common_cities[loc_l]
                    geo_info = {
                        'name': loc,
                        'latitude': lat,
                        'longitude': lon,
                        'formatted_address': f"{loc}, India",
                        'confidence': 'high'
                    }
            else:
                geo_info = self.geocode_location(loc)
            if geo_info:
                geo_tags.append(geo_info)
                if not primary_location:
                    primary_location = geo_info
        
        tagged_article['geo_tags'] = geo_tags
        tagged_article['primary_location'] = primary_location
        
        # Format for display
        if primary_location:
            tagged_article['geo_display'] = (
                f"{primary_location['name']} – "
                f"Lat: {primary_location['latitude']:.4f}°N, "
                f"Long: {primary_location['longitude']:.4f}°E"
            )
        else:
            tagged_article['geo_display'] = "Location not identified"
        
        return tagged_article

