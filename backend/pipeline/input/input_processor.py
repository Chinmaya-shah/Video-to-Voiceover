"""
Phase 1: Input Processor Module
Handles PPTX, PDF, Video files (MP4/MOV/MKV/AVI), Images (PNG/JPG), and Web URLs.
Converts presentations to high-resolution PNG slides and extracts native metadata.
"""
import os
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple

from backend.pptx_pdf_converter import (
    extract_pptx_slides_and_text,
    extract_pdf_slides_and_text,
    create_video_from_slide_images
)

logger = logging.getLogger("input_processor")

class InputProcessor:
    """
    Phase 1: Universal Input Ingestion and Normalization.
    """

    def __init__(self, upload_dir: str = "uploads", output_dir: str = "output"):
        self.upload_dir = Path(upload_dir)
        self.output_dir = Path(output_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def process_input(self, file_path: str) -> Dict[str, Any]:
        """
        Processes any input source into normalized frames/video structure.
        """
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"Input file not found: {file_path}")

        ext = p.suffix.lower()
        logger.info(f"Processing input file: {p.name} (type: {ext})")

        if ext in [".pptx", ".ppt"]:
            return self._process_pptx(p)
        elif ext in [".pdf"]:
            return self._process_pdf(p)
        elif ext in [".mp4", ".mov", ".mkv", ".avi", ".webm"]:
            return self._process_video(p)
        elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
            return self._process_image(p)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def _process_pptx(self, p: Path) -> Dict[str, Any]:
        out_slide_dir = self.output_dir / f"slides_{p.stem}"
        slides = extract_pptx_slides_and_text(str(p), str(out_slide_dir))
        image_paths = [s["image_path"] for s in slides if "image_path" in s]
        mp4_path = str(self.output_dir / f"{p.stem}_presentation.mp4")
        if image_paths:
            create_video_from_slide_images(image_paths, mp4_path, duration_per_slide=8.0)
        else:
            mp4_path = str(p)

        return {
            "source_type": "pptx",
            "file_path": str(p),
            "video_path": mp4_path,
            "slide_images": image_paths,
            "extracted_text_per_slide": [s.get("text", "") for s in slides],
            "total_slides": len(slides),
            "duration": len(slides) * 8.0
        }

    def _process_pdf(self, p: Path) -> Dict[str, Any]:
        out_slide_dir = self.output_dir / f"slides_{p.stem}"
        slides = extract_pdf_slides_and_text(str(p), str(out_slide_dir))
        image_paths = [s["image_path"] for s in slides if "image_path" in s]
        mp4_path = str(self.output_dir / f"{p.stem}_presentation.mp4")
        if image_paths:
            create_video_from_slide_images(image_paths, mp4_path, duration_per_slide=8.0)
        else:
            mp4_path = str(p)

        return {
            "source_type": "pdf",
            "file_path": str(p),
            "video_path": mp4_path,
            "slide_images": image_paths,
            "extracted_text_per_slide": [s.get("text", "") for s in slides],
            "total_slides": len(slides),
            "duration": len(slides) * 8.0
        }

    def _process_video(self, p: Path) -> Dict[str, Any]:
        return {
            "source_type": "video",
            "file_path": str(p),
            "video_path": str(p),
            "slide_images": [],
            "extracted_text_per_slide": [],
            "total_slides": 0,
            "duration": 0.0  # Timeline engine will probe duration
        }

    def _process_image(self, p: Path) -> Dict[str, Any]:
        # Single image slide presentation
        out_img_dir = self.output_dir / "single_image_slide"
        out_img_dir.mkdir(parents=True, exist_ok=True)
        dst_path = out_img_dir / p.name
        shutil.copy(p, dst_path)

        # Build 10-second video from single image
        from backend.video_stitcher import get_ffmpeg_path
        import subprocess

        video_out = str(out_img_dir / f"{p.stem}_slide.mp4")
        ffmpeg_bin = get_ffmpeg_path()
        cmd = [
            ffmpeg_bin, "-y",
            "-loop", "1", "-i", str(dst_path),
            "-c:v", "libx264", "-t", "8.0",
            "-pix_fmt", "yuv420p",
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
            video_out
        ]
        subprocess.run(cmd, capture_output=True)

        return {
            "source_type": "image",
            "file_path": str(p),
            "video_path": video_out,
            "slide_images": [str(dst_path)],
            "extracted_text_per_slide": [""],
            "total_slides": 1,
            "duration": 8.0
        }
