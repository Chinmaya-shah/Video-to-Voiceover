"""
Master Pipeline Orchestrator for 12-Stage AI Video-to-Voiceover Agent
Coordinates execution of all 12 modular phases:
Input -> Timeline -> Vision -> OCR -> Slide Intel -> Research -> Knowledge -> Narration Plan -> Script Gen -> Duration Optimizer -> TTS -> Renderer
"""
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from backend.pipeline.input.input_processor import InputProcessor
from backend.pipeline.timeline.timeline_engine import TimelineEngine
from backend.pipeline.vision.vision_engine import VisionEngine
from backend.pipeline.ocr.ocr_engine import OCREngine
from backend.pipeline.slide_intel.slide_intelligence import SlideIntelligence
from backend.pipeline.research.research_agent import ResearchAgent
from backend.pipeline.knowledge.knowledge_engine import KnowledgeEngine
from backend.pipeline.planning.narration_planner import NarrationPlanner
from backend.pipeline.script.script_generator import ScriptGenerator
from backend.pipeline.duration_optimizer.duration_optimizer import DurationOptimizer
from backend.pipeline.renderer.video_renderer import VideoRenderer

logger = logging.getLogger("pipeline_orchestrator")

class MasterPipelineOrchestrator:
    """
    Executes the 12-stage production AI Video-to-Voiceover pipeline end-to-end.
    """

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.input_processor = InputProcessor(output_dir=output_dir)
        self.timeline_engine = TimelineEngine(output_dir=output_dir)
        self.vision_engine = VisionEngine(output_dir=output_dir)
        self.ocr_engine = OCREngine(output_dir=output_dir)
        self.slide_intel = SlideIntelligence(output_dir=output_dir)
        self.research_agent = ResearchAgent(output_dir=output_dir)
        self.knowledge_engine = KnowledgeEngine(output_dir=output_dir)
        self.narration_planner = NarrationPlanner(output_dir=output_dir)
        self.script_generator = ScriptGenerator(output_dir=output_dir)
        self.duration_optimizer = DurationOptimizer(output_dir=output_dir)
        self.video_renderer = VideoRenderer(output_dir=output_dir)

    def run_pipeline(
        self,
        file_path: str,
        task_id: Optional[str] = None,
        voice_id: str = "kokoro-am_adam",
        gemini_api_key: Optional[str] = None,
        elevenlabs_api_key: Optional[str] = None,
        groq_api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes all 12 pipeline stages sequentially.
        """
        task_id = task_id or f"task_{uuid.uuid4().hex[:8]}"
        logger.info(f"=== Starting 12-Stage AI Pipeline for Task: {task_id} ===")

        # Phase 1: Input Ingestion
        input_data = self.input_processor.process_input(file_path)
        video_path = input_data["video_path"]

        # Phase 2: Timeline Engine (timeline.json)
        timeline_contract = self.timeline_engine.generate_timeline(task_id, video_path, input_data)

        # Phase 3: Vision Engine (vision.json)
        vision_contract = self.vision_engine.analyze_vision(task_id, timeline_contract, gemini_api_key)

        # Phase 4: OCR Engine (ocr.json)
        ocr_contract = self.ocr_engine.extract_ocr(task_id, timeline_contract, input_data)

        # Phase 5: Slide Intelligence (slide_intel.json)
        intel_contract = self.slide_intel.analyze_slide_intent(task_id, timeline_contract, ocr_contract, vision_contract)

        # Phase 6: Browser Research Agent (research.json)
        research_contract = self.research_agent.conduct_research(task_id, intel_contract)

        # Phase 7: Knowledge Engine (knowledge.json)
        knowledge_contract = self.knowledge_engine.build_knowledge_graph(task_id, ocr_contract, vision_contract, intel_contract, research_contract)

        # Phase 8: Narration Planner (narration_plan.json)
        plan_contract = self.narration_planner.create_plan(task_id, timeline_contract, knowledge_contract)

        # Phase 9: Script Generator (script.json)
        script_contract = self.script_generator.generate_script(task_id, timeline_contract, knowledge_contract, plan_contract, gemini_api_key, groq_api_key)

        # Phase 10 & 11: Duration Optimizer & Pluggable TTS (audio.json, target ±0.3s tolerance)
        audio_contract = self.duration_optimizer.optimize_duration(
            task_id, script_contract, timeline_contract, voice_id=voice_id, elevenlabs_api_key=elevenlabs_api_key
        )

        # Phase 12: Production Video Renderer (render.json -> final_narrated_presentation.mp4)
        render_contract = self.video_renderer.render_final_video(
            task_id, video_path, audio_contract, script_contract, timeline_contract
        )

        logger.info(f"=== 12-Stage AI Pipeline Successfully Completed for Task: {task_id} ===")

        # Build combined response
        rel_video_url = f"/output/tasks/{task_id}/final_narrated_presentation.mp4"
        rel_audio_url = f"/output/tasks/{task_id}/combined_voiceover.mp3"

        k_map = {s.slide_id: s for s in knowledge_contract.slides}
        script_list = [
            {
                "segment_id": s.slide_id,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "slide_title": (k_map[s.slide_id].slide_summary[:40] if s.slide_id in k_map and k_map[s.slide_id].slide_summary else f"Slide {s.slide_id}"),
                "narration": s.narration_text
            }
            for s in script_contract.slides
        ]

        return {
            "status": "success",
            "task_id": task_id,
            "video_url": rel_video_url,
            "audio_url": rel_audio_url,
            "script": script_list,
            "total_slides": timeline_contract.total_slides,
            "total_duration": timeline_contract.total_duration,
            "contracts_dir": f"/output/tasks/{task_id}/",
            "render": render_contract.model_dump()
        }
