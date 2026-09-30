import asyncio
import edge_tts
import logging
from typing import Optional, List
import os

logger = logging.getLogger(__name__)

# Voice mapping for languages
VOICES = {
    "en": ["en-US-JennyNeural", "en-US-GuyNeural"],
    "ta": ["ta-IN-PallaviNeural", "ta-IN-ValluvarNeural"]
}

class EdgeTTSWrapper:
    def __init__(self, language: str = "en", voice: Optional[str] = None):
        """
        Initialize the edge-tts wrapper.
        :param language: Language code ('en' or 'ta')
        :param voice: Specific voice to use. If None, the first voice for the language is used.
        """
        self.language = language
        if voice:
            self.voice = voice
        else:
            # Default to the first voice for the language
            self.voice = VOICES.get(language, ["en-US-JennyNeural"])[0]

    async def generate_audio(self, text: str, output_file: str) -> bool:
        """
        Generate audio from text and save to output_file.
        Returns True on success, False on failure.
        """
        try:
            communicate = edge_tts.Communicate(text, self.voice)
            await communicate.save(output_file)
            return True
        except Exception as e:
            logger.error(f"Error generating audio with edge-tts: {e}")
            return False

    def generate_audio_sync(self, text: str, output_file: str) -> bool:
        """
        Synchronous wrapper for generate_audio.
        """
        try:
            asyncio.run(self.generate_audio(text, output_file))
            return True
        except Exception as e:
            logger.error(f"Error in synchronous audio generation: {e}")
            return False

    @staticmethod
    def get_available_voices(language: str) -> List[str]:
        """
        Get available voices for a given language.
        """
        return VOICES.get(language, [])