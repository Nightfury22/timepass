import logging
import os
from utils.edge_tts_wrapper import EdgeTTSWrapper

logger = logging.getLogger(__name__)

class TTSAgent:
    def __init__(self):
        # We'll create a wrapper instance per call with the appropriate language
        pass

    async def generate_audio(self, text: str, language: str, output_file: str) -> bool:
        """
        Generate audio from text in the specified language and save to output_file.
        Returns True on success, False on failure.
        """
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        # Create a TTS wrapper for the given language (using default voice)
        tts_wrapper = EdgeTTSWrapper(language=language)
        # Use the synchronous method for simplicity (since we are in an async function, we can run the async method directly)
        # But note: EdgeTTSWrapper.generate_audio is async, so we should await it.
        # However, we have a synchronous wrapper that uses asyncio.run. We'll use the async method directly.
        try:
            success = await tts_wrapper.generate_audio(text, output_file)
            return success
        except Exception as e:
            logger.error(f"Error generating audio: {e}")
            return False