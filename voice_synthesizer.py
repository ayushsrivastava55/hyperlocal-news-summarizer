"""
Voice Synthesis Module
Generates audio summaries for accessibility
"""

import logging
from typing import Dict, Optional
from gtts import gTTS
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VoiceSynthesizer:
    """Generates voice output from text summaries"""
    
    def __init__(self, output_dir: str = "audio_output"):
        """
        Initialize voice synthesizer
        
        Args:
            output_dir: Directory to save audio files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Language code mapping
        self.language_codes = {
            'en': 'en',
            'hi': 'hi',
            'mr': 'mr',
            'ta': 'ta',
            'te': 'te',
            'kn': 'kn',
            'gu': 'gu',
            'bn': 'bn',
            'pa': 'pa',
            'ml': 'ml',
            'or': 'or'
        }
    
    def generate_audio(self, text: str, language: str = 'en', 
                      filename: Optional[str] = None) -> Optional[str]:
        """
        Generate audio file from text
        
        Args:
            text: Text to convert to speech
            language: Language code (e.g., 'en', 'hi', 'mr')
            filename: Optional custom filename
            
        Returns:
            Path to generated audio file, or None if failed
        """
        try:
            if not text or len(text.strip()) < 10:
                logger.warning("Text too short for audio generation")
                return None
            
            # Get language code
            lang_code = self.language_codes.get(language.lower(), 'en')
            
            # Generate filename if not provided
            if not filename:
                import hashlib
                text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
                filename = f"summary_{lang_code}_{text_hash}.mp3"
            
            filepath = self.output_dir / filename
            
            # Generate audio using gTTS
            tts = gTTS(text=text, lang=lang_code, slow=False)
            tts.save(str(filepath))
            
            logger.info(f"Generated audio file: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error generating audio: {str(e)}")
            return None
    
    def generate_multilingual_audio(self, article: Dict, 
                                   languages: list = ['en', 'mr', 'hi'], skip: bool = False) -> Dict:
        """
        Generate audio files in multiple languages
        
        Args:
            article: Article dictionary with translations
            languages: List of language codes
            
        Returns:
            Article with audio file paths added
        """
        audio_article = article.copy()
        audio_article['audio_files'] = {}
        if skip:
            return audio_article
        
        # Generate audio for each language
        for lang in languages:
            # Get text in target language
            if 'translations' in article and lang in article['translations']:
                trans = article['translations'][lang]
                text = f"{trans.get('title', '')} {trans.get('description', '')}"
            elif lang == article.get('detected_language', 'en'):
                text = f"{article.get('title', '')} {article.get('description', '')}"
            else:
                # Use summary if available
                text = article.get('ai_summary', '')
            
            if text:
                audio_path = self.generate_audio(text, lang)
                if audio_path:
                    audio_article['audio_files'][lang] = audio_path
        
        return audio_article
    
    def get_audio_url(self, filepath: str) -> str:
        """
        Get URL path for audio file (for web serving)
        
        Args:
            filepath: Path to audio file
            
        Returns:
            URL path
        """
        if filepath:
            filename = os.path.basename(filepath)
            return f"/audio/{filename}"
        return ""

