"""
NLP Processor Module
Handles text summarization and Named Entity Recognition (NER)
"""

import logging
from typing import List, Dict, Optional
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import spacy
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NLPProcessor:
    """Processes text for summarization and NER"""
    
    def __init__(self, model_name: str = "sshleifer/distilbart-cnn-12-6", lazy_load: bool = True, fast_mode: bool = False):
        """
        Initialize NLP processor
        
        Args:
            model_name: HuggingFace model for summarization
            lazy_load: If True, only load models when first used (faster startup)
            fast_mode: If True, use lightweight heuristics for speed (no HF model)
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name = model_name
        self.summarizer = None
        self.nlp = None
        self._model_loaded = False
        self.fast_mode = fast_mode
        
        logger.info(f"Using device: {self.device}")
        
        if not lazy_load and not self.fast_mode:
            self._load_models()
        else:
            logger.info("Models will be loaded on first use (lazy loading enabled)")
    
    def _load_models(self):
        """Load all models (called lazily or during init)"""
        if self.fast_mode:
            # Fast mode avoids loading heavy models entirely
            logger.info("Fast mode enabled: skipping HF summarizer load")
            # Still try to load spaCy (small) for NER
            if self.nlp is None:
                try:
                    self.nlp = spacy.load("en_core_web_sm")
                    logger.info("Loaded spaCy English model for NER (fast mode)")
                except OSError:
                    logger.warning("spaCy English model not found. Install with: python -m spacy download en_core_web_sm")
                    self.nlp = None
            self._model_loaded = True
            return
        
        if self._model_loaded:
            return
        
        logger.info("Loading NLP models...")
        
        # Initialize summarization model
        logger.info(f"Loading summarization model: {self.model_name}...")
        logger.info("This may take a few minutes on first run (downloading ~1.6GB model)...")
        try:
            self.summarizer = pipeline(
                "summarization",
                model=self.model_name,
                tokenizer=self.model_name,
                device=0 if self.device == "cuda" else -1
            )
            logger.info(f"Successfully loaded summarization model: {self.model_name}")
        except Exception as e:
            logger.warning(f"Could not load {self.model_name}, using default: {str(e)}")
            logger.info("Loading default summarization model...")
            self.summarizer = pipeline("summarization", device=-1)
            logger.info("Default summarization model loaded")
        
        # Initialize NER model (spaCy)
        try:
            # Try loading English model
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("Loaded spaCy English model for NER")
        except OSError:
            logger.warning("spaCy English model not found. Install with: python -m spacy download en_core_web_sm")
            self.nlp = None
        
        self._model_loaded = True
    
    def summarize_text(self, text: str, max_length: int = 200, 
                      min_length: int = 80) -> Dict:
        """
        Generate summary of text
        
        Args:
            text: Input text to summarize
            max_length: Maximum length of summary
            min_length: Minimum length of summary
            
        Returns:
            Dictionary with summary and metadata
        """
        # Fast path: lightweight extractive summary (lead sentences for longer summaries)
        if self.fast_mode:
            try:
                sentences = [s.strip() for s in text.split('.') if s.strip()]
                # Take more sentences for longer summary (6-10 sentences)
                num_sentences = min(10, max(6, len(sentences) // 2))
                lead = '. '.join(sentences[:num_sentences])
                if lead:
                    lead = lead + ('.' if not lead.endswith('.') else '')
                return {
                    'summary': lead,
                    'original_length': len(text),
                    'summary_length': len(lead),
                    'compression_ratio': len(lead) / len(text) if text else 0
                }
            except Exception:
                pass
        
        # Lazy load models if not already loaded (and not fast mode)
        if not self._model_loaded:
            self._load_models()
        try:
            # Always try to summarize, even for short texts
            if not text or len(text.strip()) == 0:
                return {
                    'summary': "",
                    'original_length': 0,
                    'summary_length': 0,
                    'compression_ratio': 0
                }

            # Validate text quality - skip if mostly navigation text
            text_lower = text.lower()
            nav_indicators = ['subscribe', 'login', 'newsletter', 'e-paper', 'back to the page', 'use the weekly']
            nav_count = sum(1 for phrase in nav_indicators if phrase in text_lower)
            if nav_count >= 3:
                logger.warning("Text appears to be mostly navigation content, using fallback")
                # Use extractive fallback instead
                sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 20]
                if sentences:
                    fallback = '. '.join(sentences[:3]) + '.'
                    return {
                        'summary': fallback,
                        'original_length': len(text),
                        'summary_length': len(fallback),
                        'compression_ratio': len(fallback) / len(text) if text else 0,
                        'warning': 'Navigation text detected, used extractive summary'
                    }
                else:
                    return {
                        'summary': "",
                        'original_length': len(text),
                        'summary_length': 0,
                        'compression_ratio': 0,
                        'error': 'Text quality too poor for summarization'
                    }

            # Use token-based truncation for better accuracy
            # DistilBART max input: 1024 tokens, but we'll use 512 for safety
            max_input_tokens = 512
            
            try:
                tokenizer = self.summarizer.tokenizer
                # Encode to get tokens
                tokens = tokenizer.encode(text, add_special_tokens=False, max_length=max_input_tokens, truncation=True)
                input_tokens = len(tokens)
                # Decode back to text (this ensures we don't cut mid-word)
                text = tokenizer.decode(tokens, skip_special_tokens=True)
            except Exception as e:
                # Fallback: character-based truncation (more conservative)
                logger.warning(f"Token-based truncation failed, using character-based: {e}")
                max_input_length = 2048  # Increased from 1024
                if len(text) > max_input_length:
                    text = text[:max_input_length]
                # Estimate token count (rough approximation: ~4 chars per token)
                input_tokens = len(text) // 4
            
            # Dynamically adjust max_length based on input token length
            # For longer summaries: use 60-75% of input, with higher caps
            if input_tokens < 150:
                # Short text: use 70-80% of input (min 50 tokens)
                adjusted_max = min(max_length, max(50, int(input_tokens * 0.8)))
                adjusted_min = min(min_length, max(30, int(input_tokens * 0.4)))
            elif input_tokens < 300:
                # Medium text: use 65-75% of input
                adjusted_max = min(max(max_length, 120), min(250, int(input_tokens * 0.75)))
                adjusted_min = max(min_length, min(60, int(input_tokens * 0.3)))
            else:
                # Long text: use 60-70% of input, capped at 400 tokens
                adjusted_max = min(max(max_length, 150), min(400, int(input_tokens * 0.7)))
                adjusted_min = max(min_length, min(80, int(input_tokens * 0.25)))
            
            # CRITICAL: Ensure max_length is always less than input token length
            # This prevents the warning about max_length being larger than input
            adjusted_max = min(adjusted_max, max(50, input_tokens - 5))
            adjusted_min = min(adjusted_min, max(30, adjusted_max - 30))  # Allow larger gap between min and max

            result = self.summarizer(
                text,
                max_length=adjusted_max,
                min_length=adjusted_min,
                do_sample=False
            )
            
            summary = result[0]['summary_text']
            
            return {
                'summary': summary,
                'original_length': len(text),
                'summary_length': len(summary),
                'compression_ratio': len(summary) / len(text) if text else 0
            }
            
        except Exception as e:
            logger.error(f"Error summarizing text: {str(e)}")
            # Fallback: return first few sentences (more sentences for longer summary)
            sentences = text.split('.')[:8]  # Take up to 8 sentences
            fallback_summary = '. '.join(sentences) + '.'
            return {
                'summary': fallback_summary[:max_length * 10] if max_length else fallback_summary,  # Allow longer fallback
                'original_length': len(text),
                'summary_length': len(fallback_summary[:max_length * 10] if max_length else fallback_summary),
                'compression_ratio': len(fallback_summary[:max_length * 10] if max_length else fallback_summary) / len(text) if text else 0,
                'error': str(e)
            }
    
    def extract_entities(self, text: str) -> Dict:
        """
        Extract named entities using NER
        
        Args:
            text: Input text
            
        Returns:
            Dictionary with entities categorized by type
        """
        # Lazy load models if not already loaded
        if not self._model_loaded:
            self._load_models()
        
        entities = {
            'PERSON': [],
            'ORG': [],
            'GPE': [],  # Geopolitical entities (countries, cities, states)
            'LOC': [],  # Non-GPE locations
            'DATE': [],
            'EVENT': [],
            'MISC': []
        }
        
        if not self.nlp:
            logger.warning("NER model not available")
            return entities
        
        try:
            doc = self.nlp(text)
            
            for ent in doc.ents:
                entity_type = ent.label_
                entity_text = ent.text
                
                # Map spaCy labels to our categories
                if entity_type == 'PERSON':
                    entities['PERSON'].append(entity_text)
                elif entity_type in ['ORG', 'ORGANIZATION']:
                    entities['ORG'].append(entity_text)
                elif entity_type == 'GPE':
                    entities['GPE'].append(entity_text)
                elif entity_type == 'LOC':
                    entities['LOC'].append(entity_text)
                elif entity_type == 'DATE':
                    entities['DATE'].append(entity_text)
                elif entity_type == 'EVENT':
                    entities['EVENT'].append(entity_text)
                else:
                    entities['MISC'].append(entity_text)
            
            # Remove duplicates while preserving order
            for key in entities:
                entities[key] = list(dict.fromkeys(entities[key]))
            
        except Exception as e:
            logger.error(f"Error extracting entities: {str(e)}")
        
        return entities
    
    def process_article(self, article: Dict, target_language: str = 'en') -> Dict:
        """
        Process article: summarize and extract entities
        
        Args:
            article: Article dictionary
            target_language: Language code for processing
            
        Returns:
            Article with summary and entities added
        """
        processed_article = article.copy()
        
        # Get text for summarization - prioritize raw_content if available and substantial
        # This ensures we use the full article content instead of just RSS description
        text = ""
        
        # First, try to use raw_content if available and substantial (>200 chars)
        if article.get('raw_content') and len(article['raw_content'].strip()) > 200:
            text = article['raw_content'].strip()
            logger.debug("Using raw_content for summarization")
        # Otherwise, use translated content if available
        elif 'translations' in article and target_language in article['translations']:
            trans = article['translations'][target_language]
            text = f"{trans.get('title', '')} {trans.get('description', '')}".strip()
            logger.debug(f"Using translated content ({target_language}) for summarization")
        # Fallback to original article content
        else:
            text = f"{article.get('title', '')} {article.get('description', '')}".strip()
            logger.debug("Using original article content for summarization")
        
        # Validate text quality before processing
        if not text or len(text.strip()) < 50:
            logger.warning("Text too short or empty for summarization")
            processed_article['ai_summary'] = ""
            processed_article['summary_metadata'] = {
                'original_length': 0,
                'summary_length': 0,
                'compression_ratio': 0,
                'error': 'Text too short'
            }
            processed_article['named_entities'] = {}
            processed_article['entities_formatted'] = "No entities detected"
            return processed_article
        
        # Generate summary
        summary_result = self.summarize_text(text)
        processed_article['ai_summary'] = summary_result['summary']
        processed_article['summary_metadata'] = {
            'original_length': summary_result['original_length'],
            'summary_length': summary_result['summary_length'],
            'compression_ratio': summary_result['compression_ratio']
        }
        
        # Extract entities
        entities = self.extract_entities(text)
        processed_article['named_entities'] = entities
        
        # Format entities for display
        processed_article['entities_formatted'] = self._format_entities(entities)
        
        return processed_article
    
    def _format_entities(self, entities: Dict) -> str:
        """Format entities for display in report"""
        formatted = []
        
        if entities['PERSON']:
            formatted.append(f"Persons: {', '.join(entities['PERSON'][:5])}")
        if entities['ORG']:
            formatted.append(f"Organizations: {', '.join(entities['ORG'][:5])}")
        if entities['GPE'] or entities['LOC']:
            locations = entities['GPE'] + entities['LOC']
            formatted.append(f"Locations: {', '.join(locations[:5])}")
        if entities['DATE']:
            formatted.append(f"Dates: {', '.join(entities['DATE'][:3])}")
        if entities['EVENT']:
            formatted.append(f"Events: {', '.join(entities['EVENT'][:3])}")
        
        return '; '.join(formatted) if formatted else "No entities detected"

