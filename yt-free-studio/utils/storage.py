import sqlite3
import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from models.schemas import Production, Scene, ProductionStatus, SceneStatus

class Storage:
    def __init__(self, db_path: str = "output/youtube_automation.db"):
        """
        Initialize the storage with an SQLite database.
        :param db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        # Enable WAL mode for better concurrency
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.close()
        self._init_db()

    def _init_db(self):
        """Initialize the database tables if they don't exist."""
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            cursor = conn.cursor()
            # Productions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS productions (
                    id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    format TEXT NOT NULL,
                    language TEXT NOT NULL,
                    title TEXT NOT NULL,
                    full_script TEXT NOT NULL,
                    video_prompt TEXT,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    checkpoint_data TEXT  -- JSON string for optional checkpoint
                )
            """)
            # Scenes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scenes (
                    scene_id TEXT PRIMARY KEY,
                    production_id TEXT NOT NULL,
                    `order` INTEGER NOT NULL,
                    narration TEXT NOT NULL,
                    visual_prompt TEXT NOT NULL,
                    duration_sec REAL NOT NULL,
                    camera_motion TEXT,
                    image_path TEXT,
                    audio_path TEXT,
                    status TEXT NOT NULL,
                    FOREIGN KEY (production_id) REFERENCES productions (id)
                )
            """)
            conn.commit()

    def save_production(self, production: Production) -> None:
        """
        Save a production to the database.
        If the production already exists, it will be updated.
        """
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            cursor = conn.cursor()
            # Save production
            cursor.execute("""
                INSERT OR REPLACE INTO productions (
                    id, topic, format, language, title, full_script, video_prompt, status, created_at, updated_at, checkpoint_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                production.id,
                production.topic,
                production.format,
                production.language,
                production.title,
                production.full_script,
                production.video_prompt,
                production.status.value,
                production.created_at.isoformat() if production.created_at else datetime.now().isoformat(),
                production.updated_at.isoformat() if production.updated_at else datetime.now().isoformat(),
                json.dumps(production.checkpoint_data) if production.checkpoint_data else None
            ))
            # Save scenes in the same connection
            for scene in production.scenes:
                cursor.execute("""
                    INSERT OR REPLACE INTO scenes (
                        scene_id, production_id, `order`, narration, visual_prompt, duration_sec, camera_motion, image_path, audio_path, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    scene.scene_id,
                    production.id,
                    scene.order,
                    scene.narration,
                    scene.visual_prompt,
                    scene.duration_sec,
                    scene.camera_motion,
                    scene.image_path,
                    scene.audio_path,
                    scene.status.value
                ))
            conn.commit()

    def save_scene(self, scene: Scene, production_id: str) -> None:
        """
        Save a scene to the database.
        """
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO scenes (
                    scene_id, production_id, `order`, narration, visual_prompt, duration_sec, camera_motion, image_path, audio_path, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                scene.scene_id,
                production_id,
                scene.order,
                scene.narration,
                scene.visual_prompt,
                scene.duration_sec,
                scene.camera_motion,
                scene.image_path,
                scene.audio_path,
                scene.status.value
            ))
            conn.commit()

    def get_production(self, production_id: str) -> Optional[Production]:
        """
        Retrieve a production by ID, including its scenes.
        """
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, topic, format, language, title, full_script, video_prompt, status, created_at, updated_at, checkpoint_data
                FROM productions WHERE id = ?
            """, (production_id,))
            row = cursor.fetchone()
            if not row:
                return None
            # Get scenes for this production
            cursor.execute("""
                SELECT scene_id, `order`, narration, visual_prompt, duration_sec, camera_motion, image_path, audio_path, status
                FROM scenes WHERE production_id = ? ORDER BY `order`
            """, (production_id,))
            scene_rows = cursor.fetchall()
            scenes = []
            for s_row in scene_rows:
                scene = Scene(
                    scene_id=s_row[0],
                    order=s_row[1],
                    narration=s_row[2],
                    visual_prompt=s_row[3],
                    duration_sec=s_row[4],
                    camera_motion=s_row[5],
                    image_path=s_row[6],
                    audio_path=s_row[7],
                    status=SceneStatus(s_row[8])
                )
                scenes.append(scene)
            production = Production(
                id=row[0],
                topic=row[1],
                format=row[2],
                language=row[3],
                title=row[4],
                full_script=row[5],
                scenes=scenes,
                video_prompt=row[6],
                status=ProductionStatus(row[7]),
                created_at=datetime.fromisoformat(row[8]) if row[8] else None,
                updated_at=datetime.fromisoformat(row[9]) if row[9] else None,
                checkpoint_data=json.loads(row[10]) if row[10] else None
            )
            return production

    def update_production_status(self, production_id: str, status: ProductionStatus) -> None:
        """
        Update the status of a production.
        """
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE productions SET status = ?, updated_at = ? WHERE id = ?
            """, (
                status.value,
                datetime.now().isoformat(),
                production_id
            ))
            conn.commit()

    def update_scene_status(self, scene_id: str, status: SceneStatus) -> None:
        """
        Update the status of a scene.
        """
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE scenes SET status = ? WHERE scene_id = ?
            """, (status.value, scene_id))
            conn.commit()

    def save_scene_assets(self, scene_id: str, image_path: Optional[str] = None, audio_path: Optional[str] = None) -> None:
        """
        Update the image and/or audio paths for a scene.
        """
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            cursor = conn.cursor()
            updates = []
            params = []
            if image_path is not None:
                updates.append("image_path = ?")
                params.append(image_path)
            if audio_path is not None:
                updates.append("audio_path = ?")
                params.append(audio_path)
            if not updates:
                return
            params.append(scene_id)
            query = f"UPDATE scenes SET {', '.join(updates)} WHERE scene_id = ?"
            cursor.execute(query, params)
            conn.commit()

    def list_productions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List recent productions (without scenes) for the dashboard.
        Returns a list of dictionaries with basic info.
        """
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, topic, format, language, title, status, created_at
                FROM productions ORDER BY created_at DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            productions = []
            for row in rows:
                productions.append({
                    "id": row[0],
                    "topic": row[1],
                    "format": row[2],
                    "language": row[3],
                    "title": row[4],
                    "status": row[5],
                    "created_at": row[6]
                })
            return productions

    def delete_production(self, production_id: str) -> None:
        """
        Delete a production and its scenes.
        """
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM scenes WHERE production_id = ?", (production_id,))
            cursor.execute("DELETE FROM productions WHERE id = ?", (production_id,))
            conn.commit()