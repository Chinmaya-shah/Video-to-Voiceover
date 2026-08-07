"""
Phase 12: Production Video Renderer Module
Renders original presentation frames/video, audio voiceover track, and subtitle overlays using FFmpeg.
Outputs deterministic render.json schema.
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from backend.video_stitcher import VideoStitcher
from backend.pipeline.contracts.schemas import (
    RenderContract, AudioContract, ScriptContract, TimelineContract
)

logger = logging.getLogger("video_renderer")

class VideoRenderer:
    """
    Phase 12: Final Video Composition & Subtitle Rendering Engine.
    """

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.stitcher = VideoStitcher()

    def render_final_video(
        self,
        task_id: str,
        video_path: str,
        audio_contract: AudioContract,
        script_contract: ScriptContract,
        timeline_contract: TimelineContract
    ) -> RenderContract:
        """
        Combines presentation video, audio, and burned-in subtitles into final output MP4.
        """
        task_out_dir = self.output_dir / "tasks" / task_id
        task_out_dir.mkdir(parents=True, exist_ok=True)

        final_mp4 = str(task_out_dir / "final_narrated_presentation.mp4")
        srt_path = str(task_out_dir / "subtitles.srt")

        script_segments = [
            {
                "segment_id": s.slide_id,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "narration": s.narration_text
            }
            for s in script_contract.slides
        ]

        res = self.stitcher.combine_video(
            video_path=video_path,
            audio_path=audio_contract.combined_audio_path,
            script_segments=script_segments,
            output_path=final_mp4
        )

        contract = RenderContract(
            task_id=task_id,
            final_video_path=final_mp4,
            srt_subtitles_path=srt_path,
            resolution="1080p",
            render_method=res.get("method", "ffmpeg_subtitles_filter"),
            status="success"
        )

        json_path = task_out_dir / "render.json"
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(contract.model_dump_json(indent=2))

        logger.info(f"Video Renderer completed successfully -> {final_mp4}")
        return contract
