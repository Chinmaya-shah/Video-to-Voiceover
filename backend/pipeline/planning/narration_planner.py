"""
Phase 8: Narration Planner Module
Plans presenter narrative structure, calculates Target WPM (145), word count budget,
sentence target, and emphasis points before script synthesis.
Outputs deterministic narration_plan.json schema.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from backend.pipeline.contracts.schemas import (
    NarrationPlanContract, SlideNarrationPlan, TimelineContract, KnowledgeContract
)

logger = logging.getLogger("narration_planner")

class NarrationPlanner:
    """
    Phase 8: Presenter Narration Structure & Word Budget Planner.
    """

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)

    def create_plan(
        self,
        task_id: str,
        timeline_contract: TimelineContract,
        knowledge_contract: KnowledgeContract
    ) -> NarrationPlanContract:
        """
        Calculates speaking speed, word budgets, and emphasis points. Outputs narration_plan.json.
        """
        plan_items: List[SlideNarrationPlan] = []
        target_wpm = 145  # Standard executive keynote speaking pace (2.4 words / sec)

        for slide_timeline, slide_k in zip(timeline_contract.slides, knowledge_contract.slides):
            dur = slide_timeline.duration
            target_words = max(8, int(dur * 2.25))
            
            # Sentence target allocation
            if dur <= 5.0:
                sentences = 1
            elif dur <= 12.0:
                sentences = 2
            elif dur <= 20.0:
                sentences = 3
            else:
                sentences = 4

            plan_items.append(SlideNarrationPlan(
                slide_id=slide_timeline.slide_id,
                slide_duration=dur,
                target_wpm=target_wpm,
                target_word_count=target_words,
                target_sentence_count=sentences,
                presentation_persona="Apple Keynote / YC Founder Pitch Presenter",
                emotional_tone="confident, visionary, authoritative",
                emphasis_points=slide_k.key_facts_to_highlight
            ))

        contract = NarrationPlanContract(
            task_id=task_id,
            total_duration=timeline_contract.total_duration,
            overall_persona="Apple Keynote / YC Founder Pitch Presenter",
            slides=plan_items
        )

        json_path = self.output_dir / "tasks" / task_id / "narration_plan.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(contract.model_dump_json(indent=2))

        logger.info(f"Narration Planner completed -> {json_path}")
        return contract
