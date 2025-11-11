"""
Translation Module
Handles translation to native/Indic languages
"""

import logging
from typing import Optional, Dict, List
from googletrans import Translator
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
from transformers import pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NewsTranslator:
    """Translates news articles to target languages"""
    
    def __init__(self):
        self.translator = Translator()
        self.hf_translators: Dict[str, any] = {}  # lazy-loaded HF translation pipelines per target lang
        self.supported_indic_languages = {
            'hi': 'Hindi',
            'mr': 'Marathi',
            'ta': 'Tamil',
            'te': 'Telugu',
            'kn': 'Kannada',
            'gu': 'Gujarati',
            'bn': 'Bengali',
            'pa': 'Punjabi',
            'ml': 'Malayalam',
            'or': 'Odia'
        }
        # Map target language -> preferred HF model (MarianMT)
        # Only verified working models are included. Others fallback to googletrans.
        # Verified models: hi, mr, ml
        self.hf_model_map = {
            'hi': 'Helsinki-NLP/opus-mt-en-hi',  # ✅ Verified
            'mr': 'Helsinki-NLP/opus-mt-en-mr',  # ✅ Verified
            'ml': 'Helsinki-NLP/opus-mt-en-ml',  # ✅ Verified
            # Other languages use googletrans as fallback
        }
        self.hf_failed_models = set()  # Track failed models to avoid retrying
    
    def detect_language(self, text: str) -> Optional[str]:
        """
        Detect language of input text

        Args:
            text: Input text

        Returns:
            Language code (e.g., 'en', 'hi', 'mr')
        """
        try:
            if not text or len(text.strip()) < 10:
                return None

            # Simple heuristic: check for English characters
            # If mostly ASCII, assume English
            ascii_count = sum(1 for c in text[:200] if ord(c) < 128)
            if ascii_count / min(len(text[:200]), 200) > 0.8:
                return 'en'
            else:
                return 'hi'  # Default to Hindi for Indic scripts
        except Exception as e:
            logger.error(f"Error detecting language: {str(e)}")
            return 'en'  # Default to English
    
    def translate_text(self, text: str, target_lang: str = 'en',
                      source_lang: Optional[str] = None) -> Dict:
        """
        Translate text to target language

        Args:
            text: Text to translate
            target_lang: Target language code (e.g., 'en', 'hi', 'mr')
            source_lang: Optional source language code

        Returns:
            Dictionary with translated text and metadata
        """
        try:
            if not text or len(text.strip()) < 10:
                return {
                    'translated_text': text,
                    'source_lang': source_lang or 'unknown',
                    'target_lang': target_lang,
                    'confidence': 0.0
                }

            # Truncate very long text to avoid API/model issues
            # Keep first 1000 chars for translation (good enough for summaries)
            if len(text) > 1000:
                text = text[:1000]

            # Detect source language if not provided
            if not source_lang:
                source_lang = self.detect_language(text)

            # Skip translation if source and target are the same
            if source_lang == target_lang:
                return {
                    'translated_text': text,
                    'source_lang': source_lang,
                    'target_lang': target_lang,
                    'confidence': 1.0
                }

            # Try HuggingFace models first (only for verified models)
            if source_lang == 'en' and target_lang in self.hf_model_map:
                # Skip if this model already failed
                if target_lang in self.hf_failed_models:
                    logger.debug(f"Skipping failed HF model for {target_lang}, using googletrans")
                else:
                    try:
                        model_name = self.hf_model_map.get(target_lang)
                        if target_lang not in self.hf_translators:
                            logger.info(f"Loading HF translation model for en->{target_lang}: {model_name}")
                            self.hf_translators[target_lang] = pipeline(
                                "translation",
                                model=model_name,
                                tokenizer=model_name,
                                device=-1
                            )
                        trans_pipe = self.hf_translators[target_lang]
                        # Chunk text to fit within 512 token limit (roughly 400 chars per chunk)
                        chunks = [text[i:i+400] for i in range(0, len(text), 400)]
                        translated_chunks = []
                        for chunk in chunks[:5]:  # Limit to 5 chunks (2000 chars total)
                            try:
                                out = trans_pipe(chunk, max_length=200)
                                translated_chunks.append(out[0]['translation_text'] if out and isinstance(out, list) else chunk)
                            except:
                                translated_chunks.append(chunk)  # Keep original on error
                        translated = ' '.join(translated_chunks)
                        return {
                            'translated_text': translated,
                            'source_lang': source_lang,
                            'target_lang': target_lang,
                            'confidence': 0.8
                        }
                    except Exception as hf_err:
                        logger.warning(f"HF translation failed for {source_lang}->{target_lang}: {hf_err}")
                        self.hf_failed_models.add(target_lang)  # Mark as failed to avoid retrying
            
            # Fallback to googletrans for all languages (including those without HF models)
            try:
                translation = self.translator.translate(
                    text, 
                    src=source_lang, 
                    dest=target_lang
                )
                return {
                    'translated_text': translation.text,
                    'source_lang': source_lang,
                    'target_lang': target_lang,
                    'confidence': getattr(translation, 'confidence', 0.7)
                }
            except Exception as gt_err:
                logger.warning(f"Googletrans failed for {source_lang}->{target_lang}: {gt_err}")

            # Final fallback: return original text
            return {
                'translated_text': text,
                'source_lang': source_lang or 'en',
                'target_lang': target_lang,
                'confidence': 0.0
            }
        except Exception as e:
            logger.error(f"Error translating text: {str(e)}")
            return {
                'translated_text': text,
                'source_lang': source_lang or 'unknown',
                'target_lang': target_lang,
                'confidence': 0.0,
                'error': str(e)
            }
    
    def transliterate_text(self, text: str, from_script: str = 'devanagari',
                          to_script: str = 'latin') -> str:
        """
        Transliterate Indic text between scripts
        
        Args:
            text: Text to transliterate
            from_script: Source script (devanagari, tamil, etc.)
            to_script: Target script (latin, devanagari, etc.)
            
        Returns:
            Transliterated text
        """
        try:
            return transliterate(text, from_script, to_script)
        except Exception as e:
            logger.error(f"Error transliterating: {str(e)}")
            return text
    
    def translate_article(self, article: Dict, target_languages: List[str] = ['en', 'mr', 'hi']) -> Dict:
        """
        Translate article to multiple target languages
        
        Args:
            article: Article dictionary with 'title' and 'description'
            target_languages: List of target language codes
            
        Returns:
            Article dictionary with translations added
        """
        translated_article = article.copy()
        translated_article['translations'] = {}
        
        # Detect source language
        combined_text = f"{article.get('title', '')} {article.get('description', '')}"
        source_lang = self.detect_language(combined_text)
        translated_article['detected_language'] = source_lang
        
        # Translate to each target language
        for lang in target_languages:
            if lang == source_lang:
                translated_article['translations'][lang] = {
                    'title': article.get('title', ''),
                    'description': article.get('description', ''),
                    'source_lang': source_lang,
                    'target_lang': lang
                }
            else:
                title_trans = self.translate_text(article.get('title', ''), lang, source_lang)
                desc_trans = self.translate_text(article.get('description', ''), lang, source_lang)
                
                translated_article['translations'][lang] = {
                    'title': title_trans['translated_text'],
                    'description': desc_trans['translated_text'],
                    'source_lang': source_lang,
                    'target_lang': lang,
                    'confidence': min(title_trans.get('confidence', 0), desc_trans.get('confidence', 0))
                }
        
        return translated_article
    
    def get_language_name(self, lang_code: str) -> str:
        """Get human-readable language name from code"""
        return self.supported_indic_languages.get(lang_code, lang_code.upper())

