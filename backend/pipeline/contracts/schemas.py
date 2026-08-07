"""
JSON Contract Schemas for 12-Stage AI Video-to-Voiceover Pipeline
Provides Pydantic schemas for deterministic file contracts between pipeline stages.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class SlideTimelineItem(BaseModel):
    slide_id: int
    start_time: float
    end_time: float
    duration: float
    transition_type: str = "cut"
    confidence_score: float = 1.0
    visual_similarity: float = 0.0
    thumbnail_path: Optional[str] = None
    extracted_text: Optional[str] = ""

class TimelineContract(BaseModel):
    task_id: str
    video_path: str
    total_duration: float
    total_slides: int
    slides: List[SlideTimelineItem]

class VisualElement(BaseModel):
    element_type: str  # chart, table, UI_screenshot, logo, metric, diagram, cta_button
    description: str
    bounding_box: Optional[List[int]] = None
    confidence: float = 0.9

class SlideVisionItem(BaseModel):
    slide_id: int
    elements: List[VisualElement]
    primary_visual_theme: str
    has_charts: bool = False
    has_code: bool = False
    has_ui_screenshot: bool = False

class VisionContract(BaseModel):
    task_id: str
    slides: List[SlideVisionItem]

class SlideOCRItem(BaseModel):
    slide_id: int
    title: str = ""
    headings: List[str] = Field(default_factory=list)
    bullets: List[str] = Field(default_factory=list)
    numbers_and_metrics: List[str] = Field(default_factory=list)
    speaker_notes: str = ""
    full_raw_text: str = ""

class OCRContract(BaseModel):
    task_id: str
    slides: List[SlideOCRItem]

class SlideIntelItem(BaseModel):
    slide_id: int
    slide_purpose: str  # problem, solution, traction, market, team, financial, architecture, general
    key_message: str
    business_intent: str
    priority_keywords: List[str] = Field(default_factory=list)

class SlideIntelContract(BaseModel):
    task_id: str
    presentation_topic: str
    target_audience: str
    slides: List[SlideIntelItem]

class CompanyResearchData(BaseModel):
    company_name: str
    tagline: str = ""
    founding_story: str = ""
    mission_vision: str = ""
    core_products: List[str] = Field(default_factory=list)
    funding_and_traction: str = ""
    target_market_competitors: List[str] = Field(default_factory=list)
    technology_stack: List[str] = Field(default_factory=list)
    trusted_sources: List[str] = Field(default_factory=list)

class ResearchContract(BaseModel):
    task_id: str
    query_topic: str
    research_summary: CompanyResearchData

class UnifiedKnowledgeItem(BaseModel):
    slide_id: int
    slide_summary: str
    synthesized_context: str
    key_facts_to_highlight: List[str] = Field(default_factory=list)

class KnowledgeContract(BaseModel):
    task_id: str
    overall_narrative_arc: str
    company_context: CompanyResearchData
    slides: List[UnifiedKnowledgeItem]

class SlideNarrationPlan(BaseModel):
    slide_id: int
    slide_duration: float
    target_wpm: int = 145
    target_word_count: int
    target_sentence_count: int
    presentation_persona: str = "YC Founder Pitch / Keynote Presenter"
    emotional_tone: str = "confident, inspiring, authoritative"
    emphasis_points: List[str] = Field(default_factory=list)

class NarrationPlanContract(BaseModel):
    task_id: str
    total_duration: float
    overall_persona: str
    slides: List[SlideNarrationPlan]

class SlideScriptItem(BaseModel):
    slide_id: int
    start_time: float
    end_time: float
    slide_duration: float
    narration_text: str
    word_count: int
    estimated_speaking_duration: float

class ScriptContract(BaseModel):
    task_id: str
    total_words: int
    slides: List[SlideScriptItem]

class SlideAudioItem(BaseModel):
    slide_id: int
    audio_path: str
    actual_duration: float
    target_duration: float
    duration_difference: float
    speed_scaled: bool = False
    iterations_run: int = 1

class AudioContract(BaseModel):
    task_id: str
    combined_audio_path: str
    total_audio_duration: float
    used_tts_provider: str
    voice_id: str
    slides: List[SlideAudioItem]

class RenderContract(BaseModel):
    task_id: str
    final_video_path: str
    srt_subtitles_path: str
    resolution: str = "1080p"
    render_method: str
    status: str = "success"
