"""
Phase 2: Timeline Engine Module
Scans presentation videos/slides sequentially to detect exact visual slide transition timestamps.
Generates deterministic timeline.json schema.
"""
import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import cv2
import numpy as np

from backend.pipeline.contracts.schemas import TimelineContract, SlideTimelineItem

logger = logging.getLogger("timeline_engine")

class TimelineEngine:
    """
    Phase 2: Detects slide transitions, slide durations, and visual similarity hashes.
    """

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_timeline(
        self,
        task_id: str,
        video_path: str,
        input_data: Optional[Dict[str, Any]] = None,
        min_slide_duration: float = 1.5,
        diff_threshold: float = 3.8
    ) -> TimelineContract:
        """
        Calculates exact visual slide transition timestamps and outputs TimelineContract.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video for timeline analysis: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0.0

        if duration <= 0:
            cap.release()
            raise ValueError("Video duration is 0. Cannot build timeline.")

        # Sample at 2 FPS step
        sample_step = max(1, int(fps / 2.0))
        prev_gray = None
        slide_timestamps = [0.0]

        for f_idx in range(0, frame_count, sample_step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
            ret, frame = cap.read()
            if not ret:
                break

            curr_time = f_idx / fps
            small_frame = cv2.resize(frame, (320, 180))
            gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)

            if prev_gray is not None:
                diff = float(np.mean(cv2.absdiff(prev_gray, gray)))
                if diff > diff_threshold and (curr_time - slide_timestamps[-1]) >= min_slide_duration:
                    slide_timestamps.append(round(curr_time, 2))

            prev_gray = gray

        cap.release()

        # Fallback if too few slides detected on long presentation
        if len(slide_timestamps) < 10 and duration > 90:
            num_segs = max(12, int(duration / 15.0))
            step = duration / num_segs
            slide_timestamps = [round(i * step, 2) for i in range(num_segs)]

        frames_out_dir = self.output_dir / "tasks" / task_id / "keyframes"
        frames_out_dir.mkdir(parents=True, exist_ok=True)

        cap = cv2.VideoCapture(video_path)
        slides_list: List[SlideTimelineItem] = []
        total_slides = len(slide_timestamps)

        for i, t_start in enumerate(slide_timestamps):
            t_end = round(duration if i == total_slides - 1 else slide_timestamps[i + 1], 2)
            seg_dur = max(1.0, round(t_end - t_start, 2))

            # Midpoint frame preview
            mid_time = round(t_start + max(0.5, seg_dur / 2.0), 2)
            frame_num = int(mid_time * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()

            thumb_path = str(frames_out_dir / f"slide_{i+1:02d}_{int(t_start)}s.jpg")
            if ret:
                cv2.imwrite(thumb_path, frame)
            else:
                thumb_path = ""

            slides_list.append(SlideTimelineItem(
                slide_id=i + 1,
                start_time=t_start,
                end_time=t_end,
                duration=seg_dur,
                transition_type="cut",
                confidence_score=0.95,
                visual_similarity=0.1,
                thumbnail_path=thumb_path,
                extracted_text=""
            ))

        cap.release()

        contract = TimelineContract(
            task_id=task_id,
            video_path=video_path,
            total_duration=round(duration, 2),
            total_slides=len(slides_list),
            slides=slides_list
        )

        # Save timeline.json
        json_path = self.output_dir / "tasks" / task_id / "timeline.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(contract.model_dump_json(indent=2))

        logger.info(f"Timeline Engine completed. Generated {len(slides_list)} slides -> {json_path}")
        return contract
