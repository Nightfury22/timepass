import os
import google.generativeai as genai
from typing import Optional
import logging
from dotenv import load_dotenv

# Load .env file from the project root
load_dotenv()

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini client.
        If api_key is not provided, it will be read from the environment variable GEMINI_API_KEY.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY must be set in environment or passed as argument")
        genai.configure(api_key=self.api_key)
        # Use the latest free-tier model
        self.model = genai.GenerativeModel('gemini-3.8-flash')

    def generate_text(self, prompt: str, temperature: float = 0.7, max_output_tokens: int = 2048, json_mode: bool = False) -> str:
        """
        Generate text using the Gemini model.
        """
        try:
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
            if json_mode:
                generation_config.response_mime_type = "application/json"

            response = self.model.generate_content(
                prompt,
                generation_config=generation_config,
            )
            return response.text
        except Exception as e:
            logger.error(f"Error generating text with Gemini: {e}")
            raise

    def generate_text_stream(self, prompt: str, temperature: float = 0.7, max_output_tokens: int = 2048):
        """
        Generate text stream using the Gemini model.
        Yields chunks of text as they are generated.
        """
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                ),
                stream=True
            )
            for chunk in response:
                yield chunk.text
        except Exception as e:
            logger.error(f"Error generating text stream with Gemini: {e}")
            raise