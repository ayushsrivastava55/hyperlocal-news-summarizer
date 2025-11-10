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
                    logger.info("✅ Loaded spaCy English model for NER (fast mode)")
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
        logger.info("⚠️  This may take a few minutes on first run (downloading ~1.6GB model)...")
        try:
            self.summarizer = pipeline(
                "summarization",
                model=self.model_name,
                tokenizer=self.model_name,
                device=0 if self.device == "cuda" else -1
            )
            logger.info(f"✅ Successfully loaded summarization model: {self.model_name}")
        except Exception as e:
            logger.warning(f"Could not load {self.model_name}, using default: {str(e)}")
            logger.info("Loading default summarization model...")
            self.summarizer = pipeline("summarization", device=-1)
            logger.info("✅ Default summarization model loaded")
        
        # Initialize NER model (spaCy)
        try:
            # Try loading English model
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("✅ Loaded spaCy English model for NER")
        except OSError:
            logger.warning("spaCy English model not found. Install with: python -m spacy download en_core_web_sm")
            self.nlp = None
        
        self._model_loaded = True
    
    def summarize_text(self, text: str, max_length: int = 100, 
                      min_length: int = 30) -> Dict:
        """
        Generate summary of text
        
        Args:
            text: Input text to summarize
            max_length: Maximum length of summary
            min_length: Minimum length of summary
            
        Returns:
            Dictionary with summary and metadata
        """
        # Fast path: lightweight extractive summary (lead-2 sentences)
        if self.fast_mode:
            try:
                sentences = [s.strip() for s in text.split('.') if s.strip()]
                lead = '. '.join(sentences[:2])
                if lead:
                    lead = lead + ('.' if not lead.endswith('.') else '')
                return {
                    'summary': lead[:max_length],
                    'original_length': len(text),
                    'summary_length': len(lead[:max_length]),
                    'compression_ratio': len(lead[:max_length]) / len(text) if text else 0
                }
            except Exception:
                pass
        
        # Lazy load models if not already loaded (and not fast mode)
        if not self._model_loaded:
            self._load_models()
        try:
            if not text or len(text.strip()) < 50:
                return {
                    'summary': text[:max_length] if text else "",
                    'original_length': len(text) if text else 0,
                    'summary_length': len(text[:max_length]) if text else 0,
                    'compression_ratio': 1.0
                }
            
            # Truncate if too long (models have token limits)
            max_input_length = 1024
            if len(text) > max_input_length:
                text = text[:max_input_length]
            
            result = self.summarizer(
                text,
                max_length=max_length,
                min_length=min_length,
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
            # Fallback: return first few sentences
            sentences = text.split('.')[:3]
            fallback_summary = '. '.join(sentences) + '.'
            return {
                'summary': fallback_summary[:max_length],
                'original_length': len(text),
                'summary_length': len(fallback_summary[:max_length]),
                'compression_ratio': len(fallback_summary[:max_length]) / len(text) if text else 0,
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
        
        # Get text in target language
        if 'translations' in article and target_language in article['translations']:
            trans = article['translations'][target_language]
            text = f"{trans.get('title', '')} {trans.get('description', '')}"
        else:
            text = f"{article.get('title', '')} {article.get('description', '')}"
        
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

