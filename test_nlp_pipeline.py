#!/usr/bin/env python3
"""
Test NLP Pipeline Directly
Tests summarization with known text to identify issues
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from nlp_processor import NLPProcessor
import json

# Test text - a real news article excerpt
test_text = """
Voting for the Anta Assembly bypoll in Rajasthan's Baran district began on Tuesday (November 11, 2025) morning amid tight security, with a voter turnout of 5.26% recorded till 9 a.m. The bypoll is taking place across 268 polling stations and will continue till 6 p.m. All necessary arrangements have been ensured at polling centres, according to election officials. A total of 2,28,264 voters — including 1,16,783 men and 1,11,477 women — are eligible to cast their votes in this bypoll. The bypoll was necessitated after BJP MLA Kanwar Lal Meena was disqualified following his conviction in a criminal case. The election is being closely watched as it could impact the political dynamics in the region. Security has been beefed up across the district to ensure free and fair polling.
"""

print("=" * 80)
print("NLP PIPELINE TEST")
print("=" * 80)

# Test 1: Fast mode
print("\n1. TESTING FAST MODE:")
print("-" * 80)
nlp_fast = NLPProcessor(fast_mode=True)
result_fast = nlp_fast.summarize_text(test_text)
print(f"Input length: {len(test_text)} chars")
print(f"Summary: {result_fast['summary']}")
print(f"Summary length: {result_fast['summary_length']} chars")
print(f"Compression ratio: {result_fast['compression_ratio']:.2f}")

# Test 2: Full mode (with model)
print("\n2. TESTING FULL MODE (with BART model):")
print("-" * 80)
nlp_full = NLPProcessor(fast_mode=False)
result_full = nlp_full.summarize_text(test_text)
print(f"Input length: {len(test_text)} chars")
print(f"Summary: {result_full['summary']}")
print(f"Summary length: {result_full['summary_length']} chars")
print(f"Compression ratio: {result_full['compression_ratio']:.2f}")
print(f"Original length (after truncation): {result_full['original_length']} chars")

# Test 3: Test with truncated text (simulating what happens)
print("\n3. TESTING WITH TRUNCATED TEXT (1024 chars - current behavior):")
print("-" * 80)
truncated_text = test_text[:1024]
result_truncated = nlp_full.summarize_text(truncated_text)
print(f"Input length: {len(truncated_text)} chars")
print(f"Summary: {result_truncated['summary']}")
print(f"Summary length: {result_truncated['summary_length']} chars")

# Test 4: Test process_article method
print("\n4. TESTING process_article METHOD:")
print("-" * 80)
test_article = {
    'title': 'Anta Assembly bypoll: Polling underway',
    'description': test_text.strip(),
    'translations': {
        'en': {
            'title': 'Anta Assembly bypoll: Polling underway',
            'description': test_text.strip()
        }
    }
}
processed = nlp_full.process_article(test_article, target_language='en')
print(f"Title: {processed.get('title', 'N/A')}")
print(f"AI Summary: {processed.get('ai_summary', 'N/A')}")
print(f"Summary metadata: {processed.get('summary_metadata', {})}")
print(f"Entities found: {len(processed.get('named_entities', {}).get('GPE', []))} locations")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)

