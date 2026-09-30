import logging
import json
from typing import Dict, Any
from utils.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


class ScriptAgent:
    def __init__(self, gemini_client: GeminiClient):
        self.gemini_client = gemini_client

    async def generate_script(self, topic: str, format: str, language: str) -> Dict[str, Any]:
        """
        Generate a high-retention faceless storytelling script broken into scenes.
        """

        if format == "short":
            duration_guide = "Maximum 60 seconds total. Create 4 to 5 scenes."
            structure_guide = """
            Structure for Shorts:
            1. Hook (first 3 seconds - must stop the scroll)
            2. Quick setup + tension
            3. Key insight or twist
            4. Strong payoff
            5. Soft open loop or thought-provoking ending
            """
            num_scenes_hint = "4-5 scenes"
        else:
            duration_guide = "Target 8 to 12 minutes. Create 8 to 12 scenes."
            structure_guide = """
            Structure for Long-form:
            1. Strong cinematic hook
            2. Context and world setup
            3. Rising tension / multiple insights
            4. Deep dive or climax
            5. Emotional or intellectual payoff
            6. Thoughtful ending with soft CTA
            """
            num_scenes_hint = "8-12 scenes"

        language_instruction = "Write the narration in natural, fluent English." if language == "en" else "Write the narration in natural, fluent Tamil (use proper Tamil script)."

        prompt = f"""
You are an elite faceless YouTube scriptwriter specializing in high-retention cinematic storytelling videos.

Create a script about: "{topic}"

Format: {format}
{duration_guide}
{structure_guide}

Language instruction: {language_instruction}

Style rules:
- Faceless (no talking head)
- Cinematic and emotionally engaging
- Conversational but intelligent tone
- High retention language (curiosity gaps, tension, payoff)
- Avoid robotic or Wikipedia-style writing

For every scene you must provide:
- narration: Natural spoken language that flows well when read aloud
- visual_prompt: Extremely detailed cinematic prompt optimized for AI image generation. Include:
  • Subject and action
  • Camera angle and framing
  • Lighting
  • Color grade / mood
  • Style keywords (cinematic, photorealistic, 8k, volumetric lighting, etc.)
- duration_sec: Realistic duration based on speaking speed
- camera_motion: Choose one from [static, slow zoom in, slow zoom out, pan left, pan right, tilt up, tracking shot]

Output ONLY valid JSON in this exact structure (no markdown, no extra text):

{{
  "title": "Compelling title here",
  "full_script": "Full narration concatenated as one string",
  "scenes": [
    {{
      "narration": "...",
      "visual_prompt": "...",
      "duration_sec": 12.5,
      "camera_motion": "slow zoom in"
    }}
  ]
}}
"""

        try:
            # Try with JSON mode if the client supports it
            response_text = self.gemini_client.generate_text(
                prompt,
                temperature=0.75,
                max_output_tokens=4096,
                json_mode=True
            )

            # Clean possible markdown leftovers
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            result = json.loads(response_text)

            # Basic validation
            if not all(k in result for k in ("title", "full_script", "scenes")):
                raise ValueError("Missing required keys in response")

            if not isinstance(result["scenes"], list) or len(result["scenes"]) == 0:
                raise ValueError("No scenes generated")

            logger.info(f"Successfully generated script with {len(result['scenes'])} scenes")
            return result

        except Exception as e:
            logger.error(f"Error generating script: {e}")
            # Fallback so the pipeline doesn't completely break
            fallback_scenes = 4 if format == "short" else 9
            avg_duration = 12 if format == "short" else 60

            return {
                "title": f"Untitled – {topic}",
                "full_script": f"This is a placeholder script about {topic}.",
                "scenes": [
                    {
                        "narration": f"This is scene {i+1} about {topic}.",
                        "visual_prompt": f"Cinematic shot related to {topic}, scene {i+1}, highly detailed, dramatic lighting",
                        "duration_sec": avg_duration,
                        "camera_motion": "static"
                    }
                    for i in range(fallback_scenes)
                ]
            }