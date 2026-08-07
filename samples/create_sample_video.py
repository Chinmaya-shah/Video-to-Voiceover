import os
import sys
import cv2
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def create_slide(title: str, subtitle: str, bullets: list, bg_color=(20, 24, 33), width=1280, height=720) -> np.ndarray:
    """Draw a clean modern slide image using Pillow and convert to OpenCV format."""
    image = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(image)
    
    # Try default fonts or system font
    try:
        font_title = ImageFont.truetype("arial.ttf", 44)
        font_sub = ImageFont.truetype("arial.ttf", 26)
        font_bullet = ImageFont.truetype("arial.ttf", 22)
    except Exception:
        font_title = font_sub = font_bullet = ImageFont.load_default()

    # Draw header bar accent
    draw.rectangle([60, 60, width - 60, 66], fill=(99, 102, 241)) # Indigo accent
    
    # Draw Brand Tag
    draw.text((60, 80), "NAVIK LABS · PITCH DECK", font=font_sub, fill=(165, 180, 252))

    # Draw Title
    draw.text((60, 130), title, font=font_title, fill=(255, 255, 255))
    
    # Draw Subtitle
    draw.text((60, 195), subtitle, font=font_sub, fill=(203, 213, 225))

    # Draw Bullet points in glass card container
    card_top = 260
    card_bottom = height - 80
    draw.rectangle([60, card_top, width - 60, card_bottom], fill=(30, 41, 59), outline=(71, 85, 105), width=2)

    y_pos = card_top + 40
    for bullet in bullets:
        # Bullet dot
        draw.ellipse([90, y_pos + 8, 102, y_pos + 20], fill=(129, 140, 248))
        draw.text((120, y_pos), bullet, font=font_bullet, fill=(241, 245, 249))
        y_pos += 50

    # Convert PIL Image to OpenCV BGR numpy array
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

def generate_sample_video(output_path: str = "samples/sample_pitch_deck.mp4", duration_per_slide: int = 6):
    """Generate a sample 4-slide pitch deck presentation video MP4."""
    out_dir = Path(output_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    
    slides = [
        {
            "title": "Automated Video-to-Voiceover Agent",
            "subtitle": "Transforming raw video walkthroughs into narrated executive media.",
            "bullets": [
                "Automated slide detection and visual scene analysis",
                "Natural voiceover script generation via AI browser agent",
                "High-fidelity TTS synthesis using ElevenLabs API",
                "Burned-in transcript subtitles & video assembly"
            ]
        },
        {
            "title": "The Problem in Video Marketing",
            "subtitle": "Creating narrated pitch videos is time-consuming and expensive.",
            "bullets": [
                "Manual script writing takes hours per presentation",
                "Voiceover recording requires quiet studios & equipment",
                "Video editing and subtitle syncing creates bottlenecks",
                "Scaling content across multiple products is challenging"
            ]
        },
        {
            "title": "Architecture: Browser Agent + ElevenLabs",
            "subtitle": "A 3-Phase end-to-end pipeline built for speed and precision.",
            "bullets": [
                "Phase 1: Browser-use frame capture & multimodal script synthesis",
                "Phase 2: ElevenLabs neural voice generator with custom voices",
                "Phase 3: FFmpeg compositing for audio sync and burned-in subtitles",
                "FastAPI orchestration backend with interactive Web UI"
            ]
        },
        {
            "title": "Navik Labs - Next Generation AI",
            "subtitle": "Empowering businesses with intelligent media agents.",
            "bullets": [
                "Ready for production deployment and SaaS wrapper",
                "Instant turnaround for pitch decks and feature walkthroughs",
                "Enterprise voice customization and multi-language support",
                "Thank you! Contact us at team@naviklabs.ai"
            ]
        }
    ]

    width, height = 1280, 720
    fps = 30
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    print(f"Generating sample pitch deck video at {output_path}...")

    for slide in slides:
        frame_bgr = create_slide(slide["title"], slide["subtitle"], slide["bullets"], width=width, height=height)
        # Write frames for duration_per_slide seconds
        for _ in range(duration_per_slide * fps):
            out.write(frame_bgr)

    out.release()
    print(f"Sample video created successfully! Path: {output_path}")

if __name__ == "__main__":
    generate_sample_video()
