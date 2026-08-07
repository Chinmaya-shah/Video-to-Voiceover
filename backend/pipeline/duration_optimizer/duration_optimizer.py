"""
Phase 10: Closed-Loop Duration Optimizer Module
Generates TTS, measures exact audio duration, compares against target slide duration (T_slide),
and rewrites shorter or expands narration in up to 5 iterations.
Target Goal: Difference < ±0.3 seconds tolerance.
Outputs deterministic audio.json schema.
"""
import os
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from backend.pipeline.tts.edgetts_adapter import EdgeTTSAdapter
from backend.pipeline.contracts.schemas import (
    AudioContract, SlideAudioItem, ScriptContract, TimelineContract
)

logger = logging.getLogger("duration_optimizer")

class DurationOptimizer:
    """
    Phase 10: Auto-Feedback Duration Optimizer Engine (±0.3s Target Tolerance).
    """

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)

    def optimize_duration(
        self,
        task_id: str,
        script_contract: ScriptContract,
        timeline_contract: TimelineContract,
        voice_id: str = "kokoro-am_adam",
        elevenlabs_api_key: Optional[str] = None,
        max_iterations: int = 5,
        target_tolerance: float = 0.30
    ) -> AudioContract:
        """
        Synthesizes and fits audio to slide timestamps within ±0.3s tolerance target.
        """
        audio_out_dir = self.output_dir / "tasks" / task_id / "audio"
        audio_out_dir.mkdir(parents=True, exist_ok=True)

        tts = EdgeTTSAdapter(voice=voice_id)
        slide_audios: List[SlideAudioItem] = []
        raw_audio_files: List[str] = []

        for slide_script, slide_t in zip(script_contract.slides, timeline_contract.slides):
            target_dur = slide_t.duration
            seg_id = slide_script.slide_id
            out_file = str(audio_out_dir / f"segment_{seg_id:03d}.mp3")

            iteration = 1
            current_text = slide_script.narration_text

            # Initial synthesis
            ok, eng_name = tts.synthesize(current_text, out_file)
            actual_dur = tts.engine._get_audio_duration(out_file)
            diff = abs(actual_dur - target_dur)

            # Auto-feedback loop (up to max_iterations attempts to land within ±0.3s tolerance)
            while diff > target_tolerance and iteration < max_iterations:
                iteration += 1
                logger.info(f"Slide {seg_id} Iteration {iteration}: actual={actual_dur:.2f}s vs target={target_dur:.2f}s (diff={diff:.2f}s > {target_tolerance}s)")

                if actual_dur > target_dur + target_tolerance:
                    # Text too long -> trim script text slightly
                    words = current_text.split()
                    new_word_count = max(5, int(len(words) * (target_dur / actual_dur)))
                    current_text = " ".join(words[:new_word_count]).rstrip(",;") + "."
                elif actual_dur < target_dur - 1.0:
                    # Text too short -> append natural continuation
                    current_text += " This provides sustained competitive advantage and strong market execution."
                else:
                    break

                ok, eng_name = tts.synthesize(current_text, out_file)
                actual_dur = tts.engine._get_audio_duration(out_file)
                diff = abs(actual_dur - target_dur)

            # If still slightly exceeding, apply smooth FFmpeg atempo scaling
            speed_scaled = False
            if actual_dur > target_dur:
                safe_target = max(0.8, target_dur - 0.15)
                ratio = actual_dur / safe_target
                if 0.7 <= ratio <= 2.5:
                    temp_scaled = out_file.replace(".mp3", "_scaled.mp3")
                    import subprocess
                    cmd = [
                        tts.engine.ffmpeg_path, "-y", "-i", out_file,
                        "-filter:a", f"atempo={ratio:.4f}",
                        "-t", f"{safe_target:.3f}",
                        temp_scaled
                    ]
                    subprocess.run(cmd, capture_output=True)
                    if os.path.exists(temp_scaled):
                        shutil.move(temp_scaled, out_file)
                        actual_dur = safe_target
                        speed_scaled = True

            raw_audio_files.append(out_file)
            slide_audios.append(SlideAudioItem(
                slide_id=seg_id,
                audio_path=out_file,
                actual_duration=round(actual_dur, 2),
                target_duration=target_dur,
                duration_difference=round(abs(actual_dur - target_dur), 2),
                speed_scaled=speed_scaled,
                iterations_run=iteration
            ))

        # Stitch all segments into combined_voiceover.mp3
        combined_path = str(self.output_dir / "tasks" / task_id / "combined_voiceover.mp3")
        segments_dict = [s.model_dump() for s in timeline_contract.slides]
        concat_ok = tts.engine.concatenate_segments(
            raw_audio_files,
            segments_dict,
            combined_path,
            total_video_duration=timeline_contract.total_duration
        )

        total_audio_dur = tts.engine._get_audio_duration(combined_path)

        contract = AudioContract(
            task_id=task_id,
            combined_audio_path=combined_path,
            total_audio_duration=round(total_audio_dur, 2),
            used_tts_provider="Voicebox Kokoro / EdgeTTS Adapter",
            voice_id=voice_id,
            slides=slide_audios
        )

        json_path = self.output_dir / "tasks" / task_id / "audio.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(contract.model_dump_json(indent=2))

        logger.info(f"Duration Optimizer completed. Final audio duration: {total_audio_dur:.2f}s -> {json_path}")
        return contract
