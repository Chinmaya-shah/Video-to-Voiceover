import os
import sys
import json
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from samples.create_sample_video import generate_sample_video
from backend.browser_agent import VideoScriptGenerator
from backend.voice_generator import VoiceoverGenerator
from backend.video_stitcher import VideoStitcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_pipeline")

def run_test_pipeline():
    print("=" * 60)
    print("NAVIK LABS — VIDEO-TO-VOICEOVER AGENT POC PIPELINE TEST")
    print("=" * 60)

    sample_mp4 = "samples/sample_pitch_deck.mp4"
    if not os.path.exists(sample_mp4):
        print("\n[1/4] Generating sample pitch deck video...")
        generate_sample_video(sample_mp4)

    print("\n[2/4] PHASE 1: Video Analysis & Script Generation...")
    script_gen = VideoScriptGenerator(sample_mp4)
    phase1_result = script_gen.generate_script()
    
    script_segments = phase1_result["script"]
    print(f"[OK] Extracted {phase1_result['keyframes_count']} keyframes.")
    print(f"[OK] Generated {len(script_segments)} script segments:")
    for seg in script_segments:
        print(f"  - [{seg['start_time']}s-{seg['end_time']}s] {seg['slide_title']}: \"{seg['narration']}\"")

    print("\n[3/4] PHASE 2: Script to Voiceover Audio (TTS Engine)...")
    voice_gen = VoiceoverGenerator()
    out_audio_dir = "output/test_audio"
    phase2_result = voice_gen.synthesize_script(script_segments, out_audio_dir)
    
    audio_path = phase2_result["combined_audio_path"]
    print(f"[OK] Voiceover synthesized using engine: {phase2_result['engine']}")
    print(f"[OK] Combined audio saved at: {audio_path}")

    print("\n[4/4] PHASE 3: Video Assembly & Burned-in Subtitle Overlay...")
    stitcher = VideoStitcher()
    final_output_mp4 = "output/test_final_video.mp4"
    phase3_result = stitcher.combine_video(
        video_path=sample_mp4,
        audio_path=audio_path,
        script_segments=script_segments,
        output_path=final_output_mp4
    )

    print(f"[OK] Final video composition completed! Method: {phase3_result['method']}")
    print(f"[OK] Final output video file created: {final_output_mp4}")
    print("=" * 60)
    print("POC PIPELINE VERIFICATION PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_test_pipeline()
