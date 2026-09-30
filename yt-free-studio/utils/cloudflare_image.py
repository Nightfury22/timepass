
import os
import logging
import base64
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class CloudflareImageClient:
    def __init__(self):
        self.account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        self.api_token = os.getenv("CLOUDFLARE_API_TOKEN")

        if not self.account_id or not self.api_token:
            raise ValueError(
                "CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN must be set in .env"
            )

        self.model = "@cf/black-forest-labs/flux-1-schnell"
        self.base_url = (
            f"https://api.cloudflare.com/client/v4/accounts/"
            f"{self.account_id}/ai/run/{self.model}"
        )

    def generate_image(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
    ) -> Optional[bytes]:
        """
        Generate an image using Cloudflare Workers AI.
        Returns PNG image bytes or None on failure.
        """
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        payload = {"prompt": prompt}

        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=90,
            )

            if response.status_code != 200:
                logger.error(
                    "Cloudflare error %s: %s",
                    response.status_code,
                    response.text,
                )
                return None

            result = response.json()
            image_b64 = None

            if isinstance(result.get("result"), dict):
                image_b64 = result["result"].get("image")
            elif isinstance(result.get("result"), str):
                image_b64 = result["result"]

            if not image_b64:
                logger.error("No image found in Cloudflare response: %s", result)
                return None

            return base64.b64decode(image_b64)

        except Exception:
            logger.exception("Cloudflare image generation failed")
            return None