"""
Configuration file for Hyperlocal News Summarizer
"""
import os

# Target languages for translation and audio generation
# Expanded Indic coverage
TARGET_LANGUAGES = [
    'en',  # English
    'hi',  # Hindi
    'mr',  # Marathi
    'bn',  # Bengali
    'ta',  # Tamil
    'te',  # Telugu
    'kn',  # Kannada
    'gu',  # Gujarati
    'pa',  # Punjabi
    'ml',  # Malayalam
    'or',  # Odia
]  # Add/remove here to control UI and processing languages

# Summarization model (HuggingFace)
SUMMARIZATION_MODEL = "facebook/bart-large-cnn"

# Audio output directory
AUDIO_OUTPUT_DIR = "audio_output"

# Default location for reports
DEFAULT_LOCATION = "Nagpur"

# Feed configurations (can be overridden)
DEFAULT_FEED_CONFIGS = [
    {
        'type': 'RSS',
        'url': 'https://www.lokmat.com/rss/nagpur/',
        'name': 'Lokmat Nagpur'
    },
    {
        'type': 'RSS',
        'url': 'https://timesofindia.indiatimes.com/rssfeeds/-2128833038.cms',
        'name': 'Times of India Nagpur'
    },
    {
        'type': 'RSS',
        'url': 'https://www.thehitavada.com/rss',
        'name': 'Hitavada Nagpur'
    }
]

# Flask configuration
FLASK_HOST = '0.0.0.0'
FLASK_PORT = 5000
FLASK_DEBUG = True

# Summary parameters
SUMMARY_MAX_LENGTH = 100
SUMMARY_MIN_LENGTH = 30

# NER model
NER_MODEL = "en_core_web_sm"

# SerpAPI
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
SERPAPI_ENABLED = bool(SERPAPI_API_KEY)

