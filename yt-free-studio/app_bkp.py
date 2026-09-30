import asyncio
import inspect
import logging
import os
from pathlib import Path

import streamlit as st

# Must be the first Streamlit command on this page.
# Keep this before importing project modules in case they use Streamlit too.
st.set_page_config(
    page_title="YouTube Free Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

from pipeline.orchestrator import Orchestrator
from models.schemas import ProductionStatus, SceneStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@st.cache_resource
def get_orchestrator():
    return Orchestrator()


orchestrator = get_orchestrator()


def run_async(result):
    """Handle either async methods (coroutines) or synchronous methods."""
    if inspect.isawaitable(result):
        return asyncio.run(result)
    return result


def asset_exists(path):
    return bool(path) and Path(path).is_file()


def production_status_text(production):
    status = getattr(production, "status", "unknown")
    return getattr(status, "value", str(status))


if "current_production_id" not in st.session_state:
    st.session_state.current_production_id = None


# ---------------------------------------------------------------------------
# Sidebar: create and select productions
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("🎬 YouTube Free Studio")
    st.caption("Create, review, and prepare storytelling videos.")
    st.subheader("Create New Production")

    with st.form("new_production_form", clear_on_submit=False):
        topic = st.text_input(
            "Topic",
            placeholder="e.g. The rise of AI agents in 2026",
        )
        format_option = st.selectbox(
            "Format",
            ["short", "long"],
            format_func=lambda value: (
                "Shorts (≤60 seconds)" if value == "short"
                else "Long-form (8–12 minutes)"
            ),
        )
        language_option = st.selectbox(
            "Language",
            ["en", "ta"],
            format_func=lambda value: "English" if value == "en" else "Tamil",
        )
        submitted = st.form_submit_button(
            "Create Script",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if not topic.strip():
            st.warning("Please enter a topic.")
        else:
            try:
                with st.spinner("Generating your script and scenes..."):
                    production = run_async(
                        orchestrator.create_production(
                            topic.strip(),
                            format_option,
                            language_option,
                        )
                    )
                st.session_state.current_production_id = production.id
                st.success("Script created. Review it before generating assets.")
                st.rerun()
            except Exception as exc:
                logger.exception("Production creation failed")
                st.error(f"Could not create production: {exc}")

    st.divider()
    st.subheader("Past Productions")

    try:
        productions = run_async(orchestrator.list_productions(limit=10))
        if productions:
            for item in productions:
                title = item.get("title") or item.get("topic") or "Untitled production"
                status = item.get("status", "unknown")
                fmt = item.get("format", "unknown")
                lang = item.get("language", "unknown")
                with st.expander(f"{title} · {fmt} · {lang}"):
                    st.caption(f"Status: {getattr(status, 'value', status)}")
                    st.write(f"**ID:** `{item.get('id', '')}`")
                    st.write(f"**Topic:** {item.get('topic', '')}")
                    st.write(f"**Created:** {item.get('created_at', '')}")
                    if st.button("Open production", key=f"open_{item.get('id')}"):
                        st.session_state.current_production_id = item.get("id")
                        st.rerun()
        else:
            st.info("No productions yet.")
    except Exception as exc:
        logger.exception("Could not list productions")
        st.error(f"Could not load past productions: {exc}")


# ---------------------------------------------------------------------------
# Main workspace
# ---------------------------------------------------------------------------
st.title("Production Review Studio")
st.caption("Review the script first, then generate and review assets.")

production_id = st.session_state.current_production_id
if not production_id:
    st.info("Create a production or open one from the sidebar to get started.")
    st.stop()

try:
    production = run_async(orchestrator.get_production(production_id))
except Exception as exc:
    logger.exception("Could not load production %s", production_id)
    st.error(f"Could not load this production: {exc}")
    st.stop()

if not production:
    st.error("Production not found. Select another production from the sidebar.")
    st.session_state.current_production_id = None
    st.stop()

status_text = production_status_text(production)
st.header(production.title or production.topic)
st.caption(
    f"Production ID: {production.id}  ·  "
    f"Format: {production.format}  ·  "
    f"Language: {'English' if production.language == 'en' else 'Tamil'}  ·  "
    f"Status: {status_text}"
)

tab_script, tab_assets, tab_approval = st.tabs(
    ["📝 Script Review", "🖼️ Asset Review", "✅ Approval"]
)

# ---------------------------------------------------------------------------
# Tab 1: Script review and editing
# ---------------------------------------------------------------------------
with tab_script:
    st.subheader("Title and full script")

    edited_title = st.text_input(
        "Video title",
        value=production.title or "",
        key=f"title_{production.id}",
    )
    edited_full_script = st.text_area(
        "Full script",
        value=production.full_script or "",
        height=220,
        key=f"full_script_{production.id}",
        help="Edit the overall script here. Scene narration can be edited below as well.",
    )

    if st.button("Save Title and Full Script", key="save_script_overall"):
        try:
            production.title = edited_title.strip()
            production.full_script = edited_full_script
            run_async(orchestrator.storage.save_production(production))
            st.success("Title and full script saved.")
            st.rerun()
        except Exception as exc:
            logger.exception("Could not save full script")
            st.error(f"Could not save script: {exc}")

    st.divider()
    st.subheader(f"Scenes ({len(production.scenes)})")

    for scene in production.scenes:
        with st.expander(
            f"Scene {scene.order + 1} · {scene.duration_sec:g} seconds",
            expanded=False,
        ):
            narration = st.text_area(
                "Narration",
                value=scene.narration,
                key=f"narration_{scene.scene_id}",
                height=120,
            )
            visual_prompt = st.text_area(
                "Visual prompt",
                value=scene.visual_prompt,
                key=f"visual_{scene.scene_id}",
                height=120,
            )
            duration = st.number_input(
                "Duration (seconds)",
                min_value=1.0,
                max_value=600.0,
                value=float(scene.duration_sec),
                step=0.5,
                key=f"duration_{scene.scene_id}",
            )
            camera_motion = st.text_input(
                "Camera motion",
                value=scene.camera_motion or "",
                key=f"camera_{scene.scene_id}",
            )

            if st.button("Save Scene Changes", key=f"save_scene_{scene.scene_id}"):
                try:
                    scene.narration = narration
                    scene.visual_prompt = visual_prompt
                    scene.duration_sec = duration
                    scene.camera_motion = camera_motion.strip() or None
                    run_async(orchestrator.storage.save_scene(scene, production.id))
                    st.success(f"Scene {scene.order + 1} saved.")
                    st.rerun()
                except Exception as exc:
                    logger.exception("Could not save scene %s", scene.scene_id)
                    st.error(f"Could not save scene: {exc}")

    st.divider()
    st.info(
        "Recommended workflow: save any edits above before generating assets. "
        "Asset generation may use external APIs."
    )
    if st.button("🎨 Generate Assets", type="primary", key="generate_assets"):
        try:
            with st.spinner("Generating scene images and narration audio..."):
                updated_production = run_async(
                    orchestrator.generate_assets(production.id)
                )
            st.success(
                f"Asset generation finished for {len(updated_production.scenes)} scenes."
            )
            st.rerun()
        except Exception as exc:
            logger.exception("Asset generation failed")
            st.error(f"Asset generation failed: {exc}")


# ---------------------------------------------------------------------------
# Tab 2: Asset review and per-scene regeneration
# ---------------------------------------------------------------------------
with tab_assets:
    st.subheader("Review generated images and narration")
    st.caption("You can regenerate one image or audio track without regenerating every scene.")

    for scene in production.scenes:
        with st.expander(f"Scene {scene.order + 1}", expanded=False):
            image_col, audio_col = st.columns(2)

            with image_col:
                st.markdown("**Image**")
                if asset_exists(scene.image_path):
                    st.image(scene.image_path, caption=f"Scene {scene.order + 1}", use_container_width=True)
                    st.caption(f"File: {scene.image_path}")
                else:
                    st.info("No image file found for this scene.")

                if st.button("Regenerate Image", key=f"regen_img_{scene.scene_id}"):
                    try:
                        from pipeline.image_agent import ImageAgent

                        output_dir = Path("output") / str(production.id)
                        output_dir.mkdir(parents=True, exist_ok=True)
                        image_file = output_dir / f"scene_{scene.order}_image.png"

                        with st.spinner("Generating image..."):
                            image_agent = ImageAgent()
                            success = run_async(
                                image_agent.generate_image(
                                    scene.visual_prompt,
                                    str(image_file),
                                )
                            )

                        if success and image_file.is_file():
                            scene.image_path = str(image_file)
                            run_async(
                                orchestrator.storage.save_scene_assets(
                                    scene.scene_id,
                                    image_path=str(image_file),
                                )
                            )
                            st.success("Image regenerated.")
                            st.rerun()
                        else:
                            st.error("Image generation did not produce a file. Check the terminal logs.")
                    except Exception as exc:
                        logger.exception("Image regeneration failed")
                        st.error(f"Image regeneration failed: {exc}")

            with audio_col:
                st.markdown("**Narration audio**")
                if asset_exists(scene.audio_path):
                    st.audio(scene.audio_path, format="audio/mp3")
                    st.caption(f"File: {scene.audio_path}")
                else:
                    st.info("No audio file found for this scene.")

                if st.button("Regenerate Audio", key=f"regen_audio_{scene.scene_id}"):
                    try:
                        from pipeline.tts_agent import TTSAgent

                        output_dir = Path("output") / str(production.id)
                        output_dir.mkdir(parents=True, exist_ok=True)
                        audio_file = output_dir / f"scene_{scene.order}_audio.mp3"

                        with st.spinner("Generating narration audio..."):
                            tts_agent = TTSAgent()
                            success = run_async(
                                tts_agent.generate_audio(
                                    scene.narration,
                                    production.language,
                                    str(audio_file),
                                )
                            )

                        if success and audio_file.is_file():
                            scene.audio_path = str(audio_file)
                            run_async(
                                orchestrator.storage.save_scene_assets(
                                    scene.scene_id,
                                    audio_path=str(audio_file),
                                )
                            )
                            st.success("Audio regenerated.")
                            st.rerun()
                        else:
                            st.error("Audio generation did not produce a file. Check the terminal logs.")
                    except Exception as exc:
                        logger.exception("Audio regeneration failed")
                        st.error(f"Audio regeneration failed: {exc}")

            scene_status = getattr(scene.status, "value", str(scene.status))
            st.caption(f"Scene status: {scene_status}")
            if st.button(
                "Lock Scene" if scene.status != SceneStatus.LOCKED else "Unlock Scene",
                key=f"toggle_lock_{scene.scene_id}",
            ):
                try:
                    new_status = (
                        SceneStatus.DRAFT
                        if scene.status == SceneStatus.LOCKED
                        else SceneStatus.LOCKED
                    )
                    run_async(
                        orchestrator.storage.update_scene_status(
                            scene.scene_id,
                            new_status,
                        )
                    )
                    st.success(
                        "Scene locked." if new_status == SceneStatus.LOCKED else "Scene unlocked."
                    )
                    st.rerun()
                except Exception as exc:
                    logger.exception("Could not update scene status")
                    st.error(f"Could not update scene status: {exc}")


# ---------------------------------------------------------------------------
# Tab 3: Final preview and approval
# ---------------------------------------------------------------------------
with tab_approval:
    st.subheader("Production preview")
    all_images_present = all(asset_exists(scene.image_path) for scene in production.scenes)
    all_audio_present = all(asset_exists(scene.audio_path) for scene in production.scenes)

    metric1, metric2, metric3 = st.columns(3)
    metric1.metric("Scenes", len(production.scenes))
    metric2.metric(
        "Images",
        f"{sum(asset_exists(scene.image_path) for scene in production.scenes)}/{len(production.scenes)}",
    )
    metric3.metric(
        "Audio tracks",
        f"{sum(asset_exists(scene.audio_path) for scene in production.scenes)}/{len(production.scenes)}",
    )

    for scene in production.scenes:
        with st.container():
            info_col, image_col, audio_col = st.columns([1, 2, 2])
            with info_col:
                st.markdown(f"**Scene {scene.order + 1}**")
                st.write(f"{scene.duration_sec:g} seconds")
                st.caption(
                    f"Status: {getattr(scene.status, 'value', str(scene.status))}"
                )
            with image_col:
                if asset_exists(scene.image_path):
                    st.image(scene.image_path, use_container_width=True)
                else:
                    st.info("Image not available")
            with audio_col:
                if asset_exists(scene.audio_path):
                    st.audio(scene.audio_path, format="audio/mp3")
                else:
                    st.info("Audio not available")

    st.divider()
    if production.video_prompt:
        st.subheader("Video-generation prompt")
        st.text_area(
            "Copy this prompt into your preferred AI video tool",
            value=production.video_prompt,
            height=280,
            key=f"video_prompt_{production.id}",
        )
        st.caption("To copy: click inside the text box, press Ctrl+A, then Ctrl+C.")

    approve_disabled = (
        production_status_text(production) != ProductionStatus.READY_FOR_REVIEW.value
    )
    if not all_images_present or not all_audio_present:
        st.warning("Some image or audio files are missing. Generate or regenerate them before approval.")

    approve_col, regenerate_col, reject_col = st.columns(3)

    with approve_col:
        if st.button(
            "✅ Approve Production",
            type="primary",
            disabled=approve_disabled,
            use_container_width=True,
        ):
            try:
                with st.spinner("Creating the final video-generation prompt..."):
                    run_async(orchestrator.approve_production(production.id))
                st.success("Production approved and video prompt generated.")
                st.rerun()
            except Exception as exc:
                logger.exception("Approval failed")
                st.error(f"Could not approve production: {exc}")

    with regenerate_col:
        if st.button("🔄 Regenerate All Assets", use_container_width=True):
            try:
                from pipeline.image_agent import ImageAgent
                from pipeline.tts_agent import TTSAgent

                image_agent = ImageAgent()
                tts_agent = TTSAgent()
                output_dir = Path("output") / str(production.id)
                output_dir.mkdir(parents=True, exist_ok=True)
                failures = []

                progress = st.progress(0)
                with st.spinner("Regenerating all scene assets..."):
                    for index, scene in enumerate(production.scenes):
                        image_file = output_dir / f"scene_{scene.order}_image.png"
                        audio_file = output_dir / f"scene_{scene.order}_audio.mp3"

                        try:
                            image_ok = run_async(
                                image_agent.generate_image(
                                    scene.visual_prompt,
                                    str(image_file),
                                )
                            )
                            if image_ok and image_file.is_file():
                                scene.image_path = str(image_file)
                            else:
                                failures.append(f"Scene {scene.order + 1}: image failed")
                        except Exception as exc:
                            logger.exception("Image generation failed for scene %s", scene.scene_id)
                            failures.append(f"Scene {scene.order + 1}: image error ({exc})")

                        try:
                            audio_ok = run_async(
                                tts_agent.generate_audio(
                                    scene.narration,
                                    production.language,
                                    str(audio_file),
                                )
                            )
                            if audio_ok and audio_file.is_file():
                                scene.audio_path = str(audio_file)
                            else:
                                failures.append(f"Scene {scene.order + 1}: audio failed")
                        except Exception as exc:
                            logger.exception("Audio generation failed for scene %s", scene.scene_id)
                            failures.append(f"Scene {scene.order + 1}: audio error ({exc})")

                        run_async(
                            orchestrator.storage.save_scene_assets(
                                scene.scene_id,
                                image_path=scene.image_path,
                                audio_path=scene.audio_path,
                            )
                        )
                        progress.progress((index + 1) / max(len(production.scenes), 1))

                if failures:
                    st.warning("Regeneration finished with some issues:\n\n- " + "\n- ".join(failures))
                else:
                    st.success("All scene assets regenerated successfully.")
                st.rerun()
            except Exception as exc:
                logger.exception("Bulk asset regeneration failed")
                st.error(f"Could not regenerate all assets: {exc}")

    with reject_col:
        if st.button("❌ Return to Draft", use_container_width=True):
            try:
                production.status = ProductionStatus.DRAFT
                run_async(orchestrator.storage.save_production(production))
                st.warning("Production returned to draft.")
                st.rerun()
            except Exception as exc:
                logger.exception("Could not return production to draft")
                st.error(f"Could not update production: {exc}")


st.divider()
st.caption("YouTube Free Studio · Local production workspace")
