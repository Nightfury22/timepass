import os
import logging
from typing import Optional
from huggingface_hub import InferenceClient

logger = logging.getLogger(__name__)

class HFImageClient:
    def __init__(self, api_token: Optional[str] = None, model: str = "black-forest-labs/FLUX.1-schnell"):
        """
        Initialize the Hugging Face image client.
        If api_token is not provided, it will be read from the environment variable HF_TOKEN.
        """
        self.api_token = api_token or os.getenv("HF_TOKEN")
        if not self.api_token:
            raise ValueError("HF_TOKEN must be set in environment or passed as argument")
        self.client = InferenceClient(model=model, token=self.api_token)

    def generate_image(self, prompt: str, width: int = 1024, height: int = 1024) -> Optional[bytes]:
        """
        Generate an image from a prompt using the Hugging Face Inference API.
        Returns the image bytes on success, or None on failure.
        """
        try:
            # The HF Inference API for image generation returns a PIL image or bytes?
            # We'll use the text_to_image method which returns a PIL Image.
            image = self.client.text_to_image(prompt, width=width, height=height)
            # Convert PIL image to bytes
            from io import BytesIO
            img_byte_arr = BytesIO()
            image.save(img_byte_arr, format='PNG')
            return img_byte_arr.getvalue()
        except Exception as e:
            logger.error(f"Error generating image with Hugging Face: {e}")
            return None