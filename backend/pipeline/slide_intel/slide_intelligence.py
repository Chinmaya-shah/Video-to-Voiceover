"""
Phase 5: Slide Intelligence Module
Determines slide purpose (problem, solution, traction, market, team, financial, architecture),
key message, business intent, and priority keywords. Outputs slide_intel.json.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from backend.pipeline.contracts.schemas import SlideIntelContract, SlideIntelItem, TimelineContract, OCRContract, VisionContract

logger = logging.getLogger("slide_intelligence")

class SlideIntelligence:
    """
    Phase 5: Presentation Intent & Slide Purpose Compiler.
    """

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)

    def analyze_slide_intent(
        self,
        task_id: str,
        timeline_contract: TimelineContract,
        ocr_contract: OCRContract,
        vision_contract: VisionContract
    ) -> SlideIntelContract:
        """
        Determines presentation intent and builds slide_intel.json contract.
        """
        intel_items: List[SlideIntelItem] = []
        topic = "Executive Pitch Presentation"

        for slide_ocr, slide_vision in zip(ocr_contract.slides, vision_contract.slides):
            title_lower = slide_ocr.title.lower()
            text_lower = slide_ocr.full_raw_text.lower()

            # Classify purpose
            if any(k in title_lower or k in text_lower for k in ["problem", "challenge", "friction", "pain"]):
                purpose = "problem"
                intent = "Highlight customer pain point and market friction"
            elif any(k in title_lower or k in text_lower for k in ["solution", "product", "platform", "overview"]):
                purpose = "solution"
                intent = "Present core product capabilities and technological advantage"
            elif any(k in title_lower or k in text_lower for k in ["traction", "growth", "revenue", "metric", "arr", "mrr"]):
                purpose = "traction"
                intent = "Demonstrate rapid growth momentum and commercial validation"
            elif any(k in title_lower or k in text_lower for k in ["market", "tam", "sam", "opportunity", "industry"]):
                purpose = "market"
                intent = "Establish large addressable market opportunity"
            elif any(k in title_lower or k in text_lower for k in ["team", "founder", "advisors", "leadership"]):
                purpose = "team"
                intent = "Showcase world-class leadership and domain expertise"
            elif any(k in title_lower or k in text_lower for k in ["financial", "funding", "seed", "series", "raise"]):
                purpose = "financial"
                intent = "Present investment requirements and milestone roadmap"
            elif any(k in title_lower or k in text_lower for k in ["architecture", "technology", "workflow", "engine"]):
                purpose = "architecture"
                intent = "Detail proprietary technical stack and AI workflow"
            else:
                purpose = "general"
                intent = "Communicate key strategic value proposition"

            if slide_ocr.title and slide_ocr.slide_id == 1:
                topic = slide_ocr.title

            key_msg = f"{slide_ocr.title}: {intent}"

            intel_items.append(SlideIntelItem(
                slide_id=slide_ocr.slide_id,
                slide_purpose=purpose,
                key_message=key_msg,
                business_intent=intent,
                priority_keywords=slide_ocr.numbers_and_metrics or [slide_ocr.title]
            ))

        contract = SlideIntelContract(
            task_id=task_id,
            presentation_topic=topic,
            target_audience="Investors, Executives, and Customers",
            slides=intel_items
        )

        json_path = self.output_dir / "tasks" / task_id / "slide_intel.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(contract.model_dump_json(indent=2))

        logger.info(f"Slide Intelligence completed -> {json_path}")
        return contract
