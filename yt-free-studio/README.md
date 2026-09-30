# YouTube Free Studio (yt-free-studio)

A complete local faceless content automation pipeline for creating YouTube Shorts and long-form videos in English and Tamil, using 100% free APIs (except Gemini, which the user provides).

## Features

- **Faceless Storytelling Videos**: Generate cinematic-style videos without showing a face.
- **Multiple Formats**: Support for YouTube Shorts (≤60 seconds) and long-form videos (8–12 minutes).
- **Multilingual**: Generate content in English and Tamil.
- **Human-in-the-Loop Review Studio**: Inspired by [darkzOGx/Nightfury22 youtube-automation-agent](https://github.com/darkzOGx/Nightfury22/tree/main/youtube-automation-agent), allowing users to review and edit scripts, scenes, images, and audio before final approval.
- **100% Free APIs** (except Gemini):
  - LLM: Google Gemini (user-provided API key) with optional Groq fallback.
  - Images: Pollinations.ai (primary, model=flux) with Hugging Face InferenceClient FLUX.1-schnell backup.
  - TTS: edge-tts (supports English and Tamil voices).
- **Dashboard**: Built with Streamlit for easy interaction.
- **Video Preview (Optional)**: Uses MoviePy + FFmpeg to create a simple slideshow preview.
- **State Management**: Uses SQLite and JSON files per run for persistence and resumability.
- **Configuration**: Configure via `.env` and `config.yaml`.

## Project Structure

```
yt-free-studio/
├── app.py                          # Streamlit dashboard + Review Studio
├── pipeline/
│   ├── orchestrator.py             # Coordinates the pipeline steps
│   ├── script_agent.py             # Generates script and scenes using Gemini
│   ├── image_agent.py              # Generates images using Pollinations (with HF backup)
│   ├── tts_agent.py                # Generates audio using edge-tts
│   └── video_prompt_agent.py       # Generates final video prompt for AI video tools
├── models/
│   └── schemas.py                  # Pydantic models for Scene and Production
├── utils/
│   ├── gemini_client.py            # Wrapper for Google Gemini API
│   ├── pollinations.py             # Client for Pollinations.ai image generation
│   ├── hf_image.py                 # Backup client for Hugging Face image generation
│   ├── edge_tts_wrapper.py         # Wrapper for edge-tts
│   └── storage.py                  # SQLite database and file management
├── output/                         # Stores all runs (assets, database, etc.)
├── .env.example                    # Example environment variables
├── config.yaml                     # Configuration file
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

## Core Data Models (Pydantic)

- **Scene**: Represents a single scene in the video.
  - `scene_id`: Unique identifier.
  - `order`: Sequence number.
  - `narration`: Text to be spoken.
  - `visual_prompt`: Prompt for image generation.
  - `duration_sec`: Duration in seconds.
  - `camera_motion`: Optional camera movement description.
  - `image_path`: File path to generated image.
  - `audio_path`: File path to generated audio.
  - `status`: Draft, generated, or locked.

- **Production**: Represents a video project.
  - `id`: Unique identifier.
  - `topic`: Video topic.
  - `format`: "short" or "long".
  - `language`: "en" (English) or "ta" (Tamil).
  - `title`: Video title.
  - `full_script`: Complete narration script.
  - `scenes`: List of Scene objects.
  - `video_prompt`: Final prompt for AI video tools (generated after approval).
  - `status`: Draft, generating, ready_for_review, or approved.
  - `created_at`, `updated_at`: Timestamps.
  - `checkpoint_data`: Optional data for resuming.

## Pipeline Flow (with Resume Support)

1. **Input**: User enters topic, format, and language in the Streamlit dashboard.
2. **Script Generation**: The Script Agent (using Gemini) produces a full script and a list of scenes with timing and visual prompts.
3. **Checkpoint & Review**: The production is saved and shown in the Review Studio for the user to edit the script/scenes.
4. **Asset Generation** (after user clicks "Generate Assets"):
   - Narration audio for each scene is generated using edge-tts (respecting language).
   - Images for each scene are generated using Pollinations (with Hugging Face backup).
   - Operations are performed in parallel where possible, with rate-limit handling.
5. **Second Checkpoint & Review**: The Review Studio now shows side-by-side script, scene cards (with image preview and audio player), and per-scene controls to edit text, regenerate image/audio, or lock the scene.
6. **Approval**: The user can approve the production, which triggers the generation of a final, detailed video prompt (for AI video tools like Kling, Luma, Runway) and optionally a simple MoviePy slideshow preview.
7. **Resumability**: Every production is resumable from the last successful stage via the SQLite database.

## Installation

1. **Clone the repository** (or copy the files):
   ```bash
   git clone <repository-url>
   cd yt-free-studio
   ```
   *(Note: Since we are building from scratch, you have the files in the current directory.)*

2. **Create a virtual environment** (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   - Copy `.env.example` to `.env` and fill in your Gemini API key:
     ```bash
     cp .env.example .env
     ```
   - Edit `.env` and add your `GEMINI_API_KEY` (required).
   - Optional: Add `HF_TOKEN` for Hugging Face backup image generation.

5. **(Optional) Adjust configuration**:
   - Review `config.yaml` and adjust settings as needed.

## Usage

1. **Start the Streamlit dashboard**:
   ```bash
   streamlit run app.py
   ```
2. In the browser, enter a topic, select format and language, and click "Start Production".
3. Follow the steps in the Review Studio:
   - Review and edit the script and scenes.
   - Click "Generate Assets" to create images and audio.
   - Review the generated assets, regenerate if needed, lock scenes.
   - Approve the production to get the final video prompt.
4. The output assets (images, audio) and metadata are stored in the `output/` directory.

## Notes

- **API Keys**: You must obtain a Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey) and set it in the `.env` file.
- **Rate Limits**: The pipeline includes basic retry and backoff for rate-limited APIs (especially Pollinations.ai).
- **TTS Voices**: edge-tts provides various neural voices. The default voices are:
  - English: `en-US-JennyNeural`
  - Tamil: `ta-IN-PallaviNeural`
  You can change these in `config.yaml` or by modifying the code.
- **Image Generation**: The primary image generator is Pollinations.ai (model=flux). If that fails or if you prefer Hugging Face, set `HF_TOKEN` and the backup will be used.
- **Video Prompt**: After approval, the video prompt is generated and can be copied for use with AI video tools. This project does not yet include actual video generation (e.g., with MoviePy or external AI video services), but the prompt is designed to be ready for such tools.

## Future Enhancements

- Direct video generation using MoviePy or integration with AI video APIs (Kling, Luma, Runway, etc.).
- YouTube upload and scheduling (requires OAuth2 and YouTube Data API).
- More language support (adding more TTS voices and LLM capabilities).
- Enhanced editing capabilities in the Review Studio (e.g., drag-and-drop scene reordering).
- Advanced video transitions and effects in the video prompt generation.

## License

This project is provided as-is for educational and personal use. Check the terms of the APIs used (Gemini, Pollinations, Hugging Face, edge-tts) for their respective licenses.

---

**Enjoy creating faceless videos with YouTube Free Studio!**