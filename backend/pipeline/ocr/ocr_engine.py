"""
Phase 4: OCR Engine Module
Extracts titles, headings, bullet points, numbers, statistics, and captions from slide images.
Generates deterministic ocr.json schema.
"""
import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from backend.browser_agent import extract_text_from_frame
from backend.pipeline.contracts.schemas import OCRContract, SlideOCRItem, TimelineContract

logger = logging.getLogger("ocr_engine")

class OCREngine:
    """
    Phase 4: Structured OCR and Text Hierarchy Extraction Engine.
    """

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)

    def extract_ocr(
        self,
        task_id: str,
        timeline_contract: TimelineContract,
        input_data: Optional[Dict[str, Any]] = None
    ) -> OCRContract:
        """
        Extracts structural text hierarchy per slide and outputs ocr.json.
        """
        ocr_slides: List[SlideOCRItem] = []

        for slide in timeline_contract.slides:
            raw_text = slide.extracted_text or ""
            img_path = slide.thumbnail_path

            if not raw_text and img_path and os.path.exists(img_path):
                try:
                    raw_text = extract_text_from_frame(img_path)
                except Exception as e:
                    logger.warning(f"OCR extraction warning for slide {slide.slide_id}: {e}")
                    raw_text = f"Slide {slide.slide_id}"

            lines = [l.strip() for l in raw_text.split("\n") if len(l.strip()) > 1]
            title = lines[0] if lines else f"Slide {slide.slide_id}"
            bullets = lines[1:] if len(lines) > 1 else []

            # Extract numbers/metrics
            import re
            metrics = re.findall(r'[\$€£]?\d+(?:\.\d+)?%?|\d+x|\$\d+[MKB]', raw_text)

            ocr_slides.append(SlideOCRItem(
                slide_id=slide.slide_id,
                title=title,
                headings=[title],
                bullets=bullets,
                numbers_and_metrics=metrics,
                speaker_notes="",
                full_raw_text=raw_text
            ))

        contract = OCRContract(
            task_id=task_id,
            slides=ocr_slides
        )

        json_path = self.output_dir / "tasks" / task_id / "ocr.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(contract.model_dump_json(indent=2))

        logger.info(f"OCR Engine completed for {len(ocr_slides)} slides -> {json_path}")
        return contract
