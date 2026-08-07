"""
Phase 7: Knowledge Engine Module
Merges Slide Data, OCR, Vision, Slide Intel, and Web Research into one unified Knowledge Base.
Outputs deterministic knowledge.json schema.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from backend.pipeline.contracts.schemas import (
    KnowledgeContract, UnifiedKnowledgeItem, OCRContract,
    VisionContract, SlideIntelContract, ResearchContract
)

logger = logging.getLogger("knowledge_engine")

class KnowledgeEngine:
    """
    Phase 7: Unified Knowledge Base Compiler.
    """

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)

    def build_knowledge_graph(
        self,
        task_id: str,
        ocr_contract: OCRContract,
        vision_contract: VisionContract,
        slide_intel: SlideIntelContract,
        research_contract: ResearchContract
    ) -> KnowledgeContract:
        """
        Synthesizes all multimodal inputs into knowledge.json.
        """
        knowledge_slides: List[UnifiedKnowledgeItem] = []
        research_info = research_contract.research_summary

        for slide_ocr, slide_vis, slide_intel_item in zip(
            ocr_contract.slides, vision_contract.slides, slide_intel.slides
        ):
            synth_context = (
                f"Slide Purpose: {slide_intel_item.slide_purpose.upper()}. "
                f"Title: {slide_ocr.title}. "
                f"Key Message: {slide_intel_item.key_message}. "
                f"Visible Content: {slide_ocr.full_raw_text[:300]}. "
                f"Company Core Vision: {research_info.mission_vision}."
            )

            knowledge_slides.append(UnifiedKnowledgeItem(
                slide_id=slide_ocr.slide_id,
                slide_summary=slide_intel_item.key_message,
                synthesized_context=synth_context,
                key_facts_to_highlight=slide_ocr.numbers_and_metrics or [slide_ocr.title]
            ))

        contract = KnowledgeContract(
            task_id=task_id,
            overall_narrative_arc=f"Executive founder pitch presenting {research_info.company_name}",
            company_context=research_info,
            slides=knowledge_slides
        )

        json_path = self.output_dir / "tasks" / task_id / "knowledge.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(contract.model_dump_json(indent=2))

        logger.info(f"Knowledge Engine completed for {len(knowledge_slides)} slides -> {json_path}")
        return contract
