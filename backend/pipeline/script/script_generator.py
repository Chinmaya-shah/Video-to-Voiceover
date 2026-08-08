"""
Phase 9: Script Generator Module
Calls Groq LLM (primary) -> Gemini (fallback) with REAL OCR slide text, metrics,
and company context to produce elite, pitch-quality narration per slide.
Never uses hardcoded template strings.
"""
import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from backend.pipeline.contracts.schemas import (
    ScriptContract, SlideScriptItem, TimelineContract,
    KnowledgeContract, NarrationPlanContract
)

logger = logging.getLogger("script_generator")


class ScriptGenerator:
    """
    Phase 9: AI-Powered Spoken Presenter Script Synthesizer.
    Uses Groq -> Gemini -> local fallback chain.
    """

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)

    # ------------------------------------------------------------------
    # Main entry
    # ------------------------------------------------------------------
    def generate_script(
        self,
        task_id: str,
        timeline_contract: TimelineContract,
        knowledge_contract: KnowledgeContract,
        plan_contract: NarrationPlanContract,
        gemini_api_key: Optional[str] = None,
        groq_api_key: Optional[str] = None
    ) -> ScriptContract:
        """
        Synthesizes presenter-quality narration per slide using Groq / Gemini.
        """
        groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")

        # Build a rich slide context block from all contracts
        segment_details = self._build_segment_context(
            timeline_contract, knowledge_contract, plan_contract
        )

        company_name = knowledge_contract.company_context.company_name or "the company"

        # Try Groq first (fast, free, high quality)
        raw_segments = None
        if groq_api_key:
            raw_segments = self._call_groq(segment_details, company_name, groq_api_key, timeline_contract.total_duration)

        # Fallback: Gemini
        if not raw_segments and gemini_api_key:
            raw_segments = self._call_gemini(segment_details, company_name, gemini_api_key, timeline_contract.total_duration)

        # Last resort: local OCR template (better than hardcoded blanket sentences)
        if not raw_segments:
            raw_segments = self._local_fallback(timeline_contract, knowledge_contract, plan_contract)

        # Map AI output back to contracts
        script_items = self._map_to_contract(raw_segments, timeline_contract, plan_contract)

        total_words = sum(s.word_count for s in script_items)
        contract = ScriptContract(
            task_id=task_id,
            total_words=total_words,
            slides=script_items
        )

        json_path = self.output_dir / "tasks" / task_id / "script.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(contract.model_dump_json(indent=2))

        logger.info(f"Script Generator completed ({total_words} total words, {len(script_items)} slides) -> {json_path}")
        return contract

    # ------------------------------------------------------------------
    # Context builder
    # ------------------------------------------------------------------
    def _build_segment_context(
        self,
        timeline: TimelineContract,
        knowledge: KnowledgeContract,
        plan: NarrationPlanContract
    ) -> List[Dict[str, Any]]:
        """Merge timeline, knowledge, and plan data into per-slide context dicts."""
        segments = []

        k_map = {s.slide_id: s for s in knowledge.slides}
        p_map = {s.slide_id: s for s in plan.slides}

        for slide_t in timeline.slides:
            sid = slide_t.slide_id
            slide_k = k_map.get(sid)
            slide_p = p_map.get(sid)

            ocr_text = (slide_t.extracted_text or "").strip()
            facts = slide_k.key_facts_to_highlight if slide_k else []
            summary = slide_k.slide_summary if slide_k else ""
            target_words = slide_p.target_word_count if slide_p else max(10, int(slide_t.duration * 2.3))

            segments.append({
                "slide_id": sid,
                "start_time": slide_t.start_time,
                "end_time": slide_t.end_time,
                "duration": slide_t.duration,
                "target_words": target_words,
                "ocr_text": ocr_text[:600],
                "facts": facts,
                "summary": summary,
            })
        return segments

    # ------------------------------------------------------------------
    # Groq call
    # ------------------------------------------------------------------
    def _call_groq(
        self,
        segments: List[Dict],
        company_name: str,
        api_key: str,
        total_duration: float
    ) -> Optional[List[Dict]]:
        try:
            from groq import Groq
            client = Groq(api_key=api_key)

            segment_lines = []
            for s in segments:
                facts_str = "; ".join(s["facts"][:5]) if s["facts"] else ""
                line = (
                    f"Slide {s['slide_id']} ({s['start_time']}s-{s['end_time']}s, "
                    f"Duration: {s['duration']}s, TARGET {s['target_words']} WORDS):\n"
                    f"  OCR Text on Slide: \"{s['ocr_text']}\"\n"
                    f"  Key Facts/Metrics: \"{facts_str}\"\n"
                    f"  Slide Summary: \"{s['summary']}\""
                )
                segment_lines.append(line)

            prompt = (
                f'You are an elite startup founder narrating "{company_name}" to Y Combinator / Sequoia-style investors.\n\n'
                f"SLIDE CONTENT (OCR text + metrics extracted directly from the pitch deck):\n"
                + "\n\n".join(segment_lines)
                + "\n\n"
                "NARRATION RULES — FOLLOW EXACTLY:\n"
                "1. Write narration for EVERY slide. DO NOT skip any.\n"
                "2. Match TARGET WORDS per slide precisely — this maps to speaking time.\n"
                "3. NEVER start narration with 'Looking at...', 'This slide...', 'Moving to...'.\n"
                "4. DO NOT say generic filler phrases. Reference actual numbers, names, product names, and metrics from the OCR text.\n"
                "5. Sound like a real founder speaking naturally — confident, specific, compelling.\n"
                "6. Use connectors like: 'Here's why this matters...', 'What this shows...', 'The key insight is...'.\n"
                "7. Incorporate all $ amounts, percentages, product names, team names visible in the OCR.\n"
                "8. Each slide's narration must reflect ONLY what is on that specific slide.\n\n"
                "Return ONLY a valid JSON array, no explanation:\n"
                '[\n  {"segment_id": 1, "start_time": 0.0, "end_time": 9.0, '
                '"slide_title": "Specific Title from Slide", '
                '"narration": "Spoken presenter dialogue here."}\n]'
            )

            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=6000,
                temperature=0.62
            )
            text = resp.choices[0].message.content.strip()
            return self._parse_json(text)
        except Exception as e:
            logger.warning(f"Groq script generation failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Gemini fallback
    # ------------------------------------------------------------------
    def _call_gemini(
        self,
        segments: List[Dict],
        company_name: str,
        api_key: str,
        total_duration: float
    ) -> Optional[List[Dict]]:
        try:
            from google import genai

            client = genai.Client(api_key=api_key)
            segment_lines = []
            for s in segments:
                facts_str = "; ".join(s["facts"][:5]) if s["facts"] else ""
                line = (
                    f"Slide {s['slide_id']} ({s['start_time']}s-{s['end_time']}s, "
                    f"Duration: {s['duration']}s, TARGET {s['target_words']} WORDS):\n"
                    f"  OCR Text: \"{s['ocr_text']}\"\n"
                    f"  Key Facts: \"{facts_str}\""
                )
                segment_lines.append(line)

            prompt = (
                f'You are narrating "{company_name}" pitch deck to investors.\n\n'
                "SLIDE OCR CONTENT:\n" + "\n\n".join(segment_lines) + "\n\n"
                "Write specific, metrics-driven narration per slide matching TARGET WORDS. "
                "Never use 'Looking at', 'This slide', 'Moving to'. "
                "Reference actual text, numbers, and product names from the slide OCR. "
                "Return ONLY valid JSON array:\n"
                '[{"segment_id":1,"start_time":0.0,"end_time":9.0,"slide_title":"Title","narration":"..."}]'
            )

            models = ["gemini-2.0-flash", "gemini-1.5-flash"]
            for model in models:
                try:
                    resp = client.models.generate_content(model=model, contents=[prompt])
                    return self._parse_json(resp.text.strip())
                except Exception as me:
                    logger.warning(f"Gemini model {model} failed: {me}")
                    if "429" in str(me) or "RESOURCE_EXHAUSTED" in str(me):
                        break
            return None
        except Exception as e:
            logger.warning(f"Gemini script generation failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Local OCR fallback (uses actual OCR text — not template strings)
    # ------------------------------------------------------------------
    def _local_fallback(
        self,
        timeline: TimelineContract,
        knowledge: KnowledgeContract,
        plan: NarrationPlanContract
    ) -> List[Dict]:
        k_map = {s.slide_id: s for s in knowledge.slides}
        p_map = {s.slide_id: s for s in plan.slides}
        result = []

        for slide_t in timeline.slides:
            sid = slide_t.slide_id
            slide_k = k_map.get(sid)
            slide_p = p_map.get(sid)
            ocr = (slide_t.extracted_text or "").strip()
            facts = slide_k.key_facts_to_highlight if slide_k else []
            summary = slide_k.slide_summary if slide_k else ocr[:60]
            target_words = slide_p.target_word_count if slide_p else max(10, int(slide_t.duration * 2.3))

            if ocr:
                sentences = [s.strip() for s in ocr.replace("\n", ". ").split(".") if len(s.strip()) > 4]
                narration = ". ".join(sentences[:max(1, target_words // 10)]) + "."
            elif facts:
                narration = f"{summary}. {'. '.join(facts[:3])}."
            else:
                narration = f"{summary}." if summary else f"Slide {sid} of the presentation."

            result.append({
                "segment_id": sid,
                "start_time": slide_t.start_time,
                "end_time": slide_t.end_time,
                "slide_title": summary[:50] or f"Slide {sid}",
                "narration": narration
            })
        return result

    # ------------------------------------------------------------------
    # JSON parser
    # ------------------------------------------------------------------
    def _parse_json(self, text: str) -> Optional[List[Dict]]:
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            start, end = text.find("["), text.rfind("]")
            if start != -1 and end != -1:
                text = text[start:end + 1]
            return json.loads(text)
        except Exception as e:
            logger.warning(f"JSON parse failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Map raw AI output -> SlideScriptItem contracts
    # ------------------------------------------------------------------
    def _map_to_contract(
        self,
        raw_segments: List[Dict],
        timeline: TimelineContract,
        plan: NarrationPlanContract
    ) -> List[SlideScriptItem]:
        p_map = {s.slide_id: s for s in plan.slides}
        t_map = {s.slide_id: s for s in timeline.slides}
        script_items = []

        for i, item in enumerate(raw_segments):
            sid = item.get("segment_id", i + 1)
            slide_t = t_map.get(sid)

            start_t = float(item.get("start_time", slide_t.start_time if slide_t else 0.0))
            end_t = float(item.get("end_time", slide_t.end_time if slide_t else start_t + 5.0))
            narration = str(item.get("narration", "")).strip()
            if not narration:
                narration = f"Slide {sid}."

            word_count = len(narration.split())
            est_dur = round(word_count / 2.4, 2)
            dur = round(end_t - start_t, 2)

            script_items.append(SlideScriptItem(
                slide_id=sid,
                start_time=start_t,
                end_time=end_t,
                slide_duration=dur,
                narration_text=narration,
                word_count=word_count,
                estimated_speaking_duration=est_dur
            ))

        return script_items
