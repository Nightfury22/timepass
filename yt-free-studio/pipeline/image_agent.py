import logging
import os
from typing import Optional

from utils.pollinations import PollinationsClient
from utils.hf_image import HFImageClient
from utils.cloudflare_image import CloudflareImageClient

logger = logging.getLogger(__name__)


class ImageAgent:
    def __init__(self):
        self.clients = []

        # 1. Cloudflare (best free option right now)
        try:
            self.clients.append(("Cloudflare", CloudflareImageClient()))
            logger.info("Cloudflare image client loaded")
        except Exception as e:
            logger.warning(f"Cloudflare client not available: {e}")

        # 2. Pollinations (fallback)
        try:
            self.clients.append(("Pollinations", PollinationsClient()))
            logger.info("Pollinations client loaded")
        except Exception as e:
            logger.warning(f"Pollinations client not available: {e}")

        # 3. Hugging Face (last resort)
        try:
            self.clients.append(("HuggingFace", HFImageClient()))
            logger.info("Hugging Face client loaded")
        except Exception as e:
            logger.warning(f"Hugging Face client not available: {e}")

        if not self.clients:
            logger.error("No image generation clients available!")

    async def generate_image(self, prompt: str, output_file: str) -> bool:
        """
        Try multiple providers in order until one succeeds.
        """
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        for name, client in self.clients:
            try:
                logger.info(f"Trying image generation with {name}...")
                image_bytes = client.generate_image(prompt)
                
                if image_bytes:
                    with open(output_file, "wb") as f:
                        f.write(image_bytes)
                    logger.info(f"Image generated successfully with {name}")
                    return True
                else:
                    logger.warning(f"{name} returned no image")
            except Exception as e:
                logger.warning(f"{name} failed: {e}")

        logger.error("All image providers failed")
        return False