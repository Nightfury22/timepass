import logging
from typing import List
from utils.gemini_client import GeminiClient
from models.schemas import Production, Scene

logger = logging.getLogger(__name__)

class VideoPromptAgent:
    def __init__(self, gemini_client: GeminiClient):
        self.gemini_client = gemini_client

    async def generate_video_prompt(self, production: Production) -> str:
        """
        Generate a detailed video prompt for AI video tools (like Kling, Luma, Runway) based on the approved production.
        :param production: The approved Production object.
        :return: A string containing the video prompt.
        """
        # We'll create a prompt that asks Gemini to generate a detailed video prompt.
        scenes_description = []
        for scene in production.scenes:
            scene_desc = f"""
            Scene {scene.order + 1}:
            - Narration: {scene.narration}
            - Visual: {scene.visual_prompt}
            - Duration: {scene.duration_sec} seconds
            - Camera Motion: {scene.camera_motion or 'static'}
            """
            scenes_description.append(scene_desc)

        prompt = f"""
        You are an expert in creating prompts for AI video generation tools.
        Given the following faceless video script and scene details, create a detailed video prompt that can be used with AI video tools like Kling, Luma, or Runway to generate a high-quality faceless video.

        Video Details:
        - Title: {production.title}
        - Topic: {production.topic}
        - Format: {production.format} (short: <=60s, long: 8-12 min)
        - Language: {production.language}

        Scenes:
        {''.join(scenes_description)}

        The video prompt should include:
        1. Overall style: cinematic, faceless storytelling, color grade, lighting, camera language.
        2. Pacing and mood throughout the video.
        3. Transition styles between scenes.
        4. Any specific visual effects or enhancements.
        5. Scene-by-scene description with timing, building on the provided scene details but more detailed for video generation.

        The prompt should be ready to copy-paste into an AI video tool.

        Write the prompt in a clear, descriptive manner.
        """

        try:
            video_prompt = self.gemini_client.generate_text(prompt)
            return video_prompt
        except Exception as e:
            logger.error(f"Error generating video prompt: {e}")
            # Fallback: create a basic prompt from the scenes
            fallback_prompt = f"""
            A cinematic faceless storytelling video about {production.title}.
            Style: cinematic, smooth transitions, consistent color grading, professional lighting.
            Pacing: { 'fast-paced and engaging' if production.format == 'short' else 'deliberate and informative' }.
            {chr(10).join(scenes_description)}
            """
            return fallback_prompt