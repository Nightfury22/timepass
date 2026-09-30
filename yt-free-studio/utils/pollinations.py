import requests
import urllib.parse
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class PollinationsClient:
    def __init__(self, width: int = 1024, height: int = 1024, model: str = "flux", nologo: bool = True):
        self.width = width
        self.height = height
        self.model = model
        self.nologo = nologo
        self.base_url = "https://image.pollinations.ai/prompt/"

    def generate_image(self, prompt: str, max_retries: int = 3, backoff_factor: float = 1.0) -> Optional[bytes]:
        """
        Generate an image from a prompt using the Pollinations API.
        Returns the image bytes on success, or None on failure after retries.
        """
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"{self.base_url}{encoded_prompt}?width={self.width}&height={self.height}&model={self.model}"
        if self.nologo:
            url += "&nologo=true"

        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    return response.content
                elif response.status_code == 429:  # Rate limit
                    wait_time = backoff_factor * (2 ** attempt)
                    logger.warning(f"Rate limit hit. Waiting {wait_time} seconds before retry {attempt+1}/{max_retries}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Error generating image: HTTP {response.status_code} - {response.text}")
                    return None
            except requests.RequestException as e:
                logger.error(f"Request error: {e}")
                if attempt < max_retries - 1:
                    wait_time = backoff_factor * (2 ** attempt)
                    time.sleep(wait_time)
                else:
                    return None
        logger.error(f"Failed to generate image after {max_retries} attempts.")
        return None