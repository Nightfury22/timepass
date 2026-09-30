import asyncio
import logging
import time
import uuid
import os
from typing import List, Optional, Dict, Any
from models.schemas import Production, Scene, SceneStatus, ProductionStatus
from utils.gemini_client import GeminiClient
from pipeline.script_agent import ScriptAgent
from pipeline.image_agent import ImageAgent
from pipeline.tts_agent import TTSAgent
from pipeline.video_prompt_agent import VideoPromptAgent
from utils.storage import Storage

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self):
        self.gemini_client = GeminiClient()
        self.script_agent = ScriptAgent(self.gemini_client)
        self.image_agent = ImageAgent()
        self.tts_agent = TTSAgent()
        self.video_prompt_agent = VideoPromptAgent(self.gemini_client)
        self.storage = Storage()

    async def create_production(self, topic: str, format: str, language: str) -> Production:
        """
        Create a new production from topic, format, and language.
        This generates only the script and scenes and sets status = DRAFT.
        """
        production_id = str(uuid.uuid4())
        # We'll generate a title later in the script agent, but we can set a placeholder.
        production = Production(
            id=production_id,
            topic=topic,
            format=format,
            language=language,
            title="",  # Will be set by script agent
            full_script="",
            scenes=[],
            video_prompt=None,
            status=ProductionStatus.DRAFT
        )
        # Save initial production
        self.storage.save_production(production)

        try:
            # Step 1: Generate script and scenes
            logger.info(f"Generating script for production {production_id}")
            script_result = await self.script_agent.generate_script(topic, format, language)
            # Update production with script and scenes
            production.title = script_result.get("title", f"Untitled {topic}")
            production.full_script = script_result.get("full_script", "")
            # Convert scene dicts to Scene objects
            scenes_data = script_result.get("scenes", [])
            production.scenes = []
            for i, sc in enumerate(scenes_data):
                scene = Scene(
                    scene_id=str(uuid.uuid4()),
                    order=i,
                    narration=sc.get("narration", ""),
                    visual_prompt=sc.get("visual_prompt", ""),
                    duration_sec=sc.get("duration_sec", 5.0),
                    camera_motion=sc.get("camera_motion"),
                    status=SceneStatus.DRAFT
                )
                production.scenes.append(scene)
            # Save updated production
            self.storage.save_production(production)
            logger.info(f"Script generated for production {production_id}")

            # Status remains DRAFT (script ready)
            return production

        except Exception as e:
            logger.error(f"Error in orchestration for production {production_id}: {e}")
            raise

    async def generate_assets(self, production_id: str) -> Production:
        """
        Generate assets (images and audio) for a production.
        After assets are generated, set status = READY_FOR_REVIEW.
        """
        production = self.storage.get_production(production_id)
        if not production:
            raise ValueError(f"Production {production_id} not found")

        logger.info(f"Generating assets for production {production_id}")
        # We'll update the production status to generating.
        self.storage.update_production_status(production_id, ProductionStatus.GENERATING)

        # We'll process scenes one by one for simplicity, but we can do batches.
        for scene in production.scenes:
            # Generate audio
            audio_filename = f"output/{production_id}/scene_{scene.order}_audio.mp3"
            os.makedirs(os.path.dirname(audio_filename), exist_ok=True)
            audio_success = await self.tts_agent.generate_audio(
                scene.narration,
                production.language,  # Use production language, not scene.language
                audio_filename
            )
            if audio_success:
                scene.audio_path = audio_filename
            else:
                logger.warning(f"Failed to generate audio for scene {scene.order}")

            # Generate image
            image_filename = f"output/{production_id}/scene_{scene.order}_image.png"
            os.makedirs(os.path.dirname(image_filename), exist_ok=True)
            image_success = await self.image_agent.generate_image(
                scene.visual_prompt,
                image_filename
            )
            if image_success:
                scene.image_path = image_filename
            else:
                logger.warning(f"Failed to generate image for scene {scene.order}")

            # Update scene status to generated if we have at least one asset? We'll set to GENERATED.
            self.storage.update_scene_status(scene.scene_id, SceneStatus.GENERATED)
            # Save the scene with asset paths
            self.storage.save_scene_assets(scene.scene_id, scene.image_path, scene.audio_path)

        # After all scenes are processed, update production status to ready for review
        self.storage.update_production_status(production_id, ProductionStatus.READY_FOR_REVIEW)
        logger.info(f"Production {production_id} is ready for review")

        # Save the final production state
        production = self.storage.get_production(production_id)
        return production

    async def regenerate_scene_image(self, production_id: str, scene_id: str) -> bool:
        """
        Regenerate image for a specific scene.
        Returns True on success, False on failure.
        """
        production = self.storage.get_production(production_id)
        if not production:
            logger.error(f"Production {production_id} not found")
            return False

        # Find the scene
        scene = None
        for s in production.scenes:
            if s.scene_id == scene_id:
                scene = s
                break
        if scene is None:
            logger.error(f"Scene {scene_id} not found in production {production_id}")
            return False

        # Generate image
        image_filename = f"output/{production_id}/scene_{scene.order}_image.png"
        os.makedirs(os.path.dirname(image_filename), exist_ok=True)
        image_success = await self.image_agent.generate_image(
            scene.visual_prompt,
            image_filename
        )
        if image_success:
            scene.image_path = image_filename
            # Update scene status to generated? We'll leave it as is, but we can update to GENERATED if we want.
            self.storage.update_scene_status(scene.scene_id, SceneStatus.GENERATED)
            # Save the scene with asset paths
            self.storage.save_scene_assets(scene.scene_id, scene.image_path, scene.audio_path)
            logger.info(f"Regenerated image for scene {scene_id}")
            return True
        else:
            logger.error(f"Failed to regenerate image for scene {scene_id}")
            return False

    async def regenerate_scene_audio(self, production_id: str, scene_id: str) -> bool:
        """
        Regenerate audio for a specific scene.
        Returns True on success, False on failure.
        """
        production = self.storage.get_production(production_id)
        if not production:
            logger.error(f"Production {production_id} not found")
            return False

        # Find the scene
        scene = None
        for s in production.scenes:
            if s.scene_id == scene_id:
                scene = s
                break
        if scene is None:
            logger.error(f"Scene {scene_id} not found in production {production_id}")
            return False

        # Generate audio
        audio_filename = f"output/{production_id}/scene_{scene.order}_audio.mp3"
        os.makedirs(os.path.dirname(audio_filename), exist_ok=True)
        audio_success = await self.tts_agent.generate_audio(
            scene.narration,
            production.language,  # Use production language, not scene.language
            audio_filename
        )
        if audio_success:
            scene.audio_path = audio_filename
            # Update scene status to generated? We'll leave it as is, but we can update to GENERATED if we want.
            self.storage.update_scene_status(scene.scene_id, SceneStatus.GENERATED)
            # Save the scene with asset paths
            self.storage.save_scene_assets(scene.scene_id, scene.image_path, scene.audio_path)
            logger.info(f"Regenerated audio for scene {scene_id}")
            return True
        else:
            logger.error(f"Failed to regenerate audio for scene {scene_id}")
            return False

    async def approve_production(self, production_id: str) -> Production:
        """
        Approve a production and generate the final video prompt.
        """
        production = self.storage.get_production(production_id)
        if not production:
            raise ValueError(f"Production {production_id} not found")
        if production.status != ProductionStatus.READY_FOR_REVIEW:
            raise ValueError(f"Production {production_id} is not ready for review")

        # Generate video prompt
        logger.info(f"Generating video prompt for production {production_id}")
        video_prompt = await self.video_prompt_agent.generate_video_prompt(production)
        production.video_prompt = video_prompt
        production.status = ProductionStatus.APPROVED
        self.storage.save_production(production)
        self.storage.update_production_status(production_id, ProductionStatus.APPROVED)
        logger.info(f"Production {production_id} approved")
        return production

    async def get_production(self, production_id: str) -> Optional[Production]:
        """
        Retrieve a production by ID.
        """
        return self.storage.get_production(production_id)

    async def list_productions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List recent productions.
        """
        return self.storage.list_productions(limit)