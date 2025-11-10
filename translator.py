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
        # Not all pairs may exist; we attempt and fallback gracefully.
        self.hf_model_map = {
            'hi': 'Helsinki-NLP/opus-mt-en-hi',
            'mr': 'Helsinki-NLP/opus-mt-en-mr',
            'ta': 'Helsinki-NLP/opus-mt-en-ta',
            'te': 'Helsinki-NLP/opus-mt-en-te',
            'kn': 'Helsinki-NLP/opus-mt-en-kn',
            'gu': 'Helsinki-NLP/opus-mt-en-gu',
            'bn': 'Helsinki-NLP/opus-mt-en-bn',
            'pa': 'Helsinki-NLP/opus-mt-en-pa',
            'ml': 'Helsinki-NLP/opus-mt-en-ml',
            'or': 'Helsinki-NLP/opus-mt-en-or',
        }
    
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
            
            detection = self.translator.detect(text)
            return detection.lang
        except Exception as e:
            logger.error(f"Error detecting language: {str(e)}")
            return None
    
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
            
            # Detect source language if not provided
            if not source_lang:
                detected = self.translator.detect(text)
                source_lang = detected.lang
            
            # Translate if source and target are different
            if source_lang != target_lang:
                translation = self.translator.translate(
                    text, 
                    src=source_lang, 
                    dest=target_lang
                )
                
                return {
                    'translated_text': translation.text,
                    'source_lang': source_lang,
                    'target_lang': target_lang,
                    'confidence': getattr(translation, 'confidence', 0.0)
                }
            else:
                return {
                    'translated_text': text,
                    'source_lang': source_lang,
                    'target_lang': target_lang,
                    'confidence': 1.0
                }
                
        except Exception as e:
            logger.warning(f"Primary translation failed ({source_lang or 'auto'}->{target_lang}) via googletrans: {e}")
            # HF fallback (English source only)
            if (source_lang or 'en') == 'en':
                try:
                    model_name = self.hf_model_map.get(target_lang)
                    if model_name:
                        if target_lang not in self.hf_translators:
                            logger.info(f"Loading HF translation model for en->{target_lang}: {model_name}")
                            self.hf_translators[target_lang] = pipeline(
                                "translation",
                                model=model_name,
                                tokenizer=model_name,
                                device=-1
                            )
                        trans_pipe = self.hf_translators[target_lang]
                        out = trans_pipe(text, max_length=512)
                        translated = out[0]['translation_text'] if out and isinstance(out, list) else text
                        return {
                            'translated_text': translated,
                            'source_lang': source_lang or 'en',
                            'target_lang': target_lang,
                            'confidence': 0.7
                        }
                except Exception as hf_err:
                    logger.warning(f"HF fallback failed for en->{target_lang}: {hf_err}")
            # Final fallback: return original text
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

