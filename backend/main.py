import os
import uuid
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from backend.browser_agent import VideoScriptGenerator
from backend.voice_generator import VoiceoverGenerator
from backend.video_stitcher import VideoStitcher
from backend.credentials_manager import CredentialsManager
from backend.pipeline.orchestrator import MasterPipelineOrchestrator

from fastapi.responses import JSONResponse
from fastapi import Request

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main_server")

cred_manager = CredentialsManager()

app = FastAPI(
    title="Navik Labs - Video-to-Voiceover Agent API",
    description="POC API for browser agent video analysis, ElevenLabs voiceover generation, and video composition.",
    version="1.0.0"
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception in API request: {exc}", exc_info=True)
    err_msg = str(exc) or "An unexpected server error occurred."
    return JSONResponse(
        status_code=400,
        content={"status": "error", "error": err_msg, "detail": err_msg}
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
SAMPLES_DIR = BASE_DIR / "samples"
FRONTEND_DIR = BASE_DIR / "frontend"

for d in [UPLOADS_DIR, OUTPUT_DIR, SAMPLES_DIR, FRONTEND_DIR]:
    d.mkdir(parents=True, exist_ok=True)

app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
app.mount("/samples", StaticFiles(directory=str(SAMPLES_DIR)), name="samples")

# Global in-memory task status storage
tasks_db: Dict[str, Dict[str, Any]] = {}

class SaveKeysRequest(BaseModel):
    elevenlabs_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None

class ProcessScriptRequest(BaseModel):
    video_path: str
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

class GenerateAudioRequest(BaseModel):
    script_segments: List[Dict[str, Any]]
    voice_id: Optional[str] = "kokoro-af_heart"
    elevenlabs_api_key: Optional[str] = None
    total_video_duration: Optional[float] = 0.0

class CombineVideoRequest(BaseModel):
    video_path: str
    audio_path: str
    script_segments: List[Dict[str, Any]]

class RunPipelineRequest(BaseModel):
    video_path: Optional[str] = None
    use_sample: Optional[bool] = True
    voice_id: Optional[str] = "kokoro-af_heart"
    elevenlabs_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

@app.get("/api/settings/get-keys")
def get_key_status():
    return cred_manager.get_masked_status()

@app.post("/api/settings/save-keys")
def save_keys(req: SaveKeysRequest):
    status = cred_manager.save_keys(
        elevenlabs_key=req.elevenlabs_api_key,
        gemini_key=req.gemini_api_key,
        groq_key=req.groq_api_key
    )
    return {"status": "success", "credentials": status}

@app.get("/api/voices")
def get_voices():
    vg = VoiceoverGenerator()
    return {"voices": vg.get_available_voices()}

@app.get("/api/status/{task_id}")
def get_task_status(task_id: str):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks_db[task_id]

@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower() or ".mp4"
    valid_exts = [".mp4", ".webm", ".mov", ".avi", ".mkv", ".pptx", ".ppt", ".pdf", ".docx"]
    if ext not in valid_exts:
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload a pitch deck (.pptx, .pdf) or video file (.mp4, .mov).")
        
    file_id = f"file_{uuid.uuid4().hex[:8]}"
    dest_path = UPLOADS_DIR / f"{file_id}{ext}"
    
    with open(dest_path, "wb") as f:
        content = await file.read()
        f.write(content)
        
    final_video_path = str(dest_path)
    web_url = f"/uploads/{file_id}{ext}"

    # If user uploaded a PPTX / PDF document, extract slide images and auto-create baseline MP4 presentation video
    if ext in [".pptx", ".ppt", ".pdf", ".docx"]:
        from backend.pptx_pdf_converter import extract_pptx_slides_and_text, extract_pdf_slides_and_text, create_video_from_slide_images
        slide_out_dir = UPLOADS_DIR / f"slides_{file_id}"
        
        if ext in [".pptx", ".ppt"]:
            slides = extract_pptx_slides_and_text(str(dest_path), str(slide_out_dir))
        elif ext == ".pdf":
            slides = extract_pdf_slides_and_text(str(dest_path), str(slide_out_dir))
        else:
            from backend.pptx_pdf_converter import convert_docx_to_images
            img_paths = convert_docx_to_images(str(dest_path), str(slide_out_dir))
            slides = [{"image_path": p} for p in img_paths]

        if slides:
            image_paths = [s["image_path"] for s in slides if "image_path" in s]
            mp4_presentation_path = str(UPLOADS_DIR / f"{file_id}_presentation.mp4")
            create_video_from_slide_images(image_paths, mp4_presentation_path, duration_per_slide=6.0)
            final_video_path = mp4_presentation_path
            web_url = f"/uploads/{file_id}_presentation.mp4"

    return {
        "status": "success",
        "filename": file.filename,
        "file_type": ext,
        "video_path": final_video_path,
        "url": web_url
    }

@app.get("/api/sample-video")
def get_sample_video(deck_id: Optional[int] = 1):
    sample_files = {
        1: "sample_pitch_deck.mp4",
        2: "tech_startup_deck.mp4",
        3: "saas_walkthrough_deck.mp4"
    }
    filename = sample_files.get(deck_id, "sample_pitch_deck.mp4")
    sample_file = SAMPLES_DIR / filename

    return {
        "status": "success",
        "video_path": str(sample_file),
        "url": f"/samples/{filename}"
    }

@app.post("/api/phase1/generate-script")
def phase1_generate_script(req: ProcessScriptRequest):
    video_path = req.video_path
    if not os.path.exists(video_path):
        raise HTTPException(status_code=400, detail=f"Video path not found: {video_path}")

    gem_key = req.gemini_api_key or cred_manager.get_gemini_key()
    generator = VideoScriptGenerator(video_path, gemini_api_key=gem_key, openai_api_key=req.openai_api_key)
    result = generator.generate_script()
    return result

@app.post("/api/phase2/generate-audio")
def phase2_generate_audio(req: GenerateAudioRequest):
    task_out_dir = OUTPUT_DIR / f"audio_{uuid.uuid4().hex[:8]}"
    el_key = req.elevenlabs_api_key or cred_manager.get_elevenlabs_key()
    vg = VoiceoverGenerator(elevenlabs_api_key=el_key)
    result = vg.synthesize_script(
        req.script_segments,
        str(task_out_dir),
        voice_id=req.voice_id or "kokoro-af_heart",
        total_video_duration=req.total_video_duration or 0.0
    )

    # Relative web URLs
    rel_path = Path(result["combined_audio_path"]).relative_to(BASE_DIR)
    result["audio_url"] = f"/{rel_path.as_posix()}"
    return result

@app.post("/api/phase3/combine-video")
def phase3_combine_video(req: CombineVideoRequest):
    output_filename = f"final_output_{uuid.uuid4().hex[:8]}.mp4"
    output_path = str(OUTPUT_DIR / output_filename)
    
    stitcher = VideoStitcher()
    result = stitcher.combine_video(
        req.video_path,
        req.audio_path,
        req.script_segments,
        output_path
    )
    
    result["video_url"] = f"/output/{output_filename}"
    return result

def run_full_pipeline_background(task_id: str, req: RunPipelineRequest):
    try:
        tasks_db[task_id] = {
            "status": "processing",
            "current_phase": 1,
            "progress_percent": 10,
            "message": "Phase 1: Analyzing video frames & generating script..."
        }
        
        video_path = req.video_path
        if not video_path or not os.path.exists(video_path):
            raise ValueError("No video file uploaded. Please upload a video file (.mp4) first before running the pipeline.")
            
        gem_key = req.gemini_api_key or cred_manager.get_gemini_key()
        el_key = req.elevenlabs_api_key or cred_manager.get_elevenlabs_key()

        # Step 1: Phase 1 Script Generation
        generator = VideoScriptGenerator(video_path, gemini_api_key=gem_key)
        phase1_res = generator.generate_script()
        script_segments = phase1_res.get("script", [])

        tasks_db[task_id].update({
            "current_phase": 2,
            "progress_percent": 45,
            "message": "Phase 2: Synthesizing voiceover audio via ElevenLabs...",
            "phase1_data": phase1_res
        })

        # Step 2: Phase 2 Audio Generation
        audio_out_dir = OUTPUT_DIR / f"pipeline_{task_id}"
        vg = VoiceoverGenerator(elevenlabs_api_key=el_key)
        phase2_res = vg.synthesize_script(
            script_segments,
            str(audio_out_dir),
            voice_id=req.voice_id or "21m00Tcm4TlvDq8ikWAM"
        )
        audio_path = phase2_res["combined_audio_path"]
        
        tasks_db[task_id].update({
            "current_phase": 3,
            "progress_percent": 75,
            "message": "Phase 3: Merging video, audio track & burning in subtitles...",
            "phase2_data": phase2_res
        })
        
        # Step 3: Phase 3 Video Assembly
        final_video_name = f"final_video_{task_id}.mp4"
        final_video_path = str(OUTPUT_DIR / final_video_name)
        
        stitcher = VideoStitcher()
        phase3_res = stitcher.combine_video(
            video_path,
            audio_path,
            script_segments,
            final_video_path
        )
        
        tasks_db[task_id].update({
            "status": "completed",
            "current_phase": 3,
            "progress_percent": 100,
            "message": "Pipeline completed successfully!",
            "phase3_data": phase3_res,
            "result": {
                "script_segments": script_segments,
                "audio_url": f"/output/pipeline_{task_id}/combined_voiceover.mp3",
                "final_video_url": f"/output/{final_video_name}",
                "engine_used": phase2_res.get("engine")
            }
        })
    except Exception as e:
        logger.error(f"Error in pipeline execution: {e}", exc_info=True)
        tasks_db[task_id] = {
            "status": "failed",
            "error": str(e),
            "message": f"Pipeline failed: {str(e)}"
        }

@app.post("/api/pipeline/run-all")
def start_pipeline(req: RunPipelineRequest, background_tasks: BackgroundTasks):
    task_id = uuid.uuid4().hex[:10]
    tasks_db[task_id] = {
        "status": "queued",
        "current_phase": 0,
        "progress_percent": 0,
        "message": "Task queued..."
    }
    background_tasks.add_task(run_full_pipeline_background, task_id, req)
@app.post("/api/pipeline/run-full")
def run_full_12stage_pipeline(req: RunPipelineRequest):
    video_path = req.video_path
    if not video_path or not os.path.exists(video_path):
        raise HTTPException(status_code=400, detail=f"Video file not found: {video_path}")

    orchestrator = MasterPipelineOrchestrator(output_dir=str(OUTPUT_DIR))
    gem_key = req.gemini_api_key or cred_manager.get_gemini_key()
    el_key = req.elevenlabs_api_key or cred_manager.get_elevenlabs_key()
    groq_key = cred_manager.get_groq_key()

    result = orchestrator.run_pipeline(
        file_path=video_path,
        voice_id=req.voice_id or "kokoro-am_adam",
        gemini_api_key=gem_key,
        elevenlabs_api_key=el_key,
        groq_api_key=groq_key
    )
    return result

@app.get("/api/pipeline/contracts/{task_id}")
def get_pipeline_contracts(task_id: str):
    task_dir = OUTPUT_DIR / "tasks" / task_id
    if not task_dir.exists():
        raise HTTPException(status_code=404, detail=f"Task contract directory not found: {task_id}")

    contracts = {}
    for contract_file in ["timeline.json", "vision.json", "ocr.json", "slide_intel.json", "research.json", "knowledge.json", "narration_plan.json", "script.json", "audio.json", "render.json"]:
        c_path = task_dir / contract_file
        if c_path.exists():
            with open(c_path, "r", encoding="utf-8") as f:
                contracts[contract_file.replace(".json", "")] = json.load(f)

    return {"status": "success", "task_id": task_id, "contracts": contracts}

app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
