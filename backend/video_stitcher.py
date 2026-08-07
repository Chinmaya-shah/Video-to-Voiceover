import os
import sys
import json
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

import cv2
import imageio_ffmpeg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("video_stitcher")

def get_ffmpeg_path() -> str:
    try:
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        logger.warning(f"Could not get imageio_ffmpeg path: {e}, falling back to 'ffmpeg'")
        return "ffmpeg"

class VideoStitcher:
    """
    Phase 3: Combine original video, synthesized ElevenLabs voiceover audio,
    and transcription subtitle overlay into a final output MP4.
    """

    def __init__(self):
        self.ffmpeg_path = get_ffmpeg_path()

    @staticmethod
    def format_srt_timestamp(seconds: float) -> str:
        """Convert float seconds into SRT timestamp string HH:MM:SS,mmm"""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int(round((seconds - int(seconds)) * 1000))
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

    def generate_srt_subtitles(self, script_segments: List[Dict[str, Any]], srt_path: str) -> str:
        """Generate SRT subtitle file from script segments."""
        srt_lines = []
        for i, seg in enumerate(script_segments, start=1):
            start_t = seg.get("start_time", 0.0)
            end_t = seg.get("end_time", start_t + 5.0)
            narration = seg.get("narration", "").strip()

            if not narration:
                continue

            start_str = self.format_srt_timestamp(start_t)
            end_str = self.format_srt_timestamp(end_t)

            srt_lines.append(f"{i}")
            srt_lines.append(f"{start_str} --> {end_str}")
            srt_lines.append(narration)
            srt_lines.append("")

        srt_content = "\n".join(srt_lines)
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

        logger.info(f"Generated SRT subtitles at {srt_path}")
        return srt_path

    def burn_subtitles_cv2(self, video_path: str, audio_path: str, script_segments: List[Dict[str, Any]], output_path: str) -> bool:
        """
        Fallback video frame subtitle overlay drawer using OpenCV if FFmpeg subtitle filter fails.
        Draws sleek dark semi-transparent pill container with centered white bold text.
        """
        logger.info("Using OpenCV subtitle overlay compositor...")
        temp_no_audio_video = str(Path(output_path).parent / "temp_no_audio.mp4")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return False

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_no_audio_video, fourcc, fps, (width, height))

        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            current_time = frame_idx / fps

            # Find active narration segment
            active_text = ""
            for seg in script_segments:
                if seg.get("start_time", 0) <= current_time <= seg.get("end_time", 0):
                    active_text = seg.get("narration", "")
                    break

            if active_text:
                # Render subtitle text box at bottom
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = max(0.6, width / 1200.0)
                thickness = 2
                
                # Split long text if needed
                max_chars = 45
                words = active_text.split()
                lines = []
                curr_line = ""
                for w in words:
                    if len(curr_line) + len(w) + 1 > max_chars:
                        lines.append(curr_line)
                        curr_line = w
                    else:
                        curr_line = (curr_line + " " + w).strip()
                if curr_line:
                    lines.append(curr_line)

                # Draw subtitle background box
                text_height_total = len(lines) * 30
                box_y1 = height - 50 - text_height_total
                box_y2 = height - 20
                
                overlay = frame.copy()
                cv2.rectangle(overlay, (40, box_y1 - 10), (width - 40, box_y2 + 10), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

                y_offset = box_y1 + 20
                for line in lines:
                    text_size, _ = cv2.getTextSize(line, font, font_scale, thickness)
                    text_x = (width - text_size[0]) // 2
                    cv2.putText(frame, line, (text_x, y_offset), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
                    y_offset += 30

            out.write(frame)
            frame_idx += 1

        cap.release()
        out.release()

        # Merge audio using FFmpeg
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", temp_no_audio_video,
            "-i", audio_path,
            "-c:v", "libx264",
            "-c:a", "aac",
            "-shortest",
            output_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.exists(temp_no_audio_video):
            os.remove(temp_no_audio_video)

        return res.returncode == 0

    def combine_video(
        self,
        video_path: str,
        audio_path: str,
        script_segments: List[Dict[str, Any]],
        output_path: str
    ) -> Dict[str, Any]:
        """
        Merge video, audio, and burn in subtitles into output file.
        """
        out_dir = Path(output_path).parent
        out_dir.mkdir(parents=True, exist_ok=True)
        
        srt_path = str(out_dir / "subtitles.srt")
        self.generate_srt_subtitles(script_segments, srt_path)

        # Sanitize srt path for FFmpeg filter on Windows
        srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")
        
        vf_filter = f"subtitles='{srt_escaped}':force_style='Fontname=Arial,FontSize=18,PrimaryColour=&H00FFFFFF,BackColour=&H80000000,BorderStyle=4,MarginV=30'"

        cmd = [
            self.ffmpeg_path, "-y",
            "-i", video_path,
            "-i", audio_path,
            "-vf", vf_filter,
            "-c:v", "libx264",
            "-c:a", "aac",
            "-shortest",
            output_path
        ]

        logger.info(f"Executing FFmpeg video stitch command: {' '.join(cmd)}")
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if process.returncode == 0 and os.path.exists(output_path):
            logger.info(f"Video stitching successful: {output_path}")
            return {
                "status": "success",
                "method": "ffmpeg_subtitles_filter",
                "srt_path": srt_path,
                "output_video_path": output_path
            }

        logger.warning(f"FFmpeg subtitle filter returned non-zero code ({process.returncode}). Trying text overlay compositor.")
        success_cv2 = self.burn_subtitles_cv2(video_path, audio_path, script_segments, output_path)

        if success_cv2 and os.path.exists(output_path):
            return {
                "status": "success",
                "method": "opencv_overlay",
                "srt_path": srt_path,
                "output_video_path": output_path
            }
        else:
            raise RuntimeError(f"Video Stitching Failed (FFmpeg exit code {process.returncode}): {process.stderr[:300]}")

if __name__ == "__main__":
    vs = VideoStitcher()
    print("VideoStitcher initialized with FFmpeg:", vs.ffmpeg_path)
