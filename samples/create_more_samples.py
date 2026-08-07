import os
import cv2
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def create_slide(title: str, subtitle: str, bullets: list, bg_color=(15, 23, 42), accent_color=(37, 99, 235), width=1280, height=720) -> np.ndarray:
    """Draw a clean modern slide image using Pillow."""
    image = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(image)
    
    try:
        font_title = ImageFont.truetype("arial.ttf", 42)
        font_sub = ImageFont.truetype("arial.ttf", 24)
        font_bullet = ImageFont.truetype("arial.ttf", 22)
    except Exception:
        font_title = font_sub = font_bullet = ImageFont.load_default()

    # Draw header bar accent
    draw.rectangle([60, 60, width - 60, 66], fill=accent_color)
    
    # Draw Brand Tag
    draw.text((60, 80), "DEMO PITCH DECK · NAVIK LABS", font=font_sub, fill=(148, 163, 184))

    # Draw Title
    draw.text((60, 130), title, font=font_title, fill=(255, 255, 255))
    
    # Draw Subtitle
    draw.text((60, 195), subtitle, font=font_sub, fill=(203, 213, 225))

    # Draw Card container
    card_top = 260
    card_bottom = height - 80
    draw.rectangle([60, card_top, width - 60, card_bottom], fill=(30, 41, 59), outline=(51, 65, 85), width=2)

    y_pos = card_top + 40
    for bullet in bullets:
        draw.ellipse([90, y_pos + 8, 102, y_pos + 20], fill=accent_color)
        draw.text((120, y_pos), bullet, font=font_bullet, fill=(241, 245, 249))
        y_pos += 50

    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

def generate_video(output_path: str, slides: list, accent_color=(37, 99, 235), duration_per_slide: int = 5):
    out_dir = Path(output_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    width, height = 1280, 720
    fps = 30
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    print(f"Generating {output_path}...")
    for slide in slides:
        frame = create_slide(slide["title"], slide["subtitle"], slide["bullets"], accent_color=accent_color, width=width, height=height)
        for _ in range(duration_per_slide * fps):
            out.write(frame)
    out.release()
    print(f"Created: {output_path}")

if __name__ == "__main__":
    # Deck 1: Tech Startup Pitch
    generate_video(
        "samples/tech_startup_deck.mp4",
        [
            {
                "title": "Nexus AI — Next-Gen Agent Infrastructure",
                "subtitle": "Building enterprise cognitive workflows for autonomous computing.",
                "bullets": [
                    "Unified agent orchestration across multi-cloud environments",
                    "Sub-100ms multi-modal reasoning latency",
                    "Enterprise security and SOC2 compliance built-in",
                    "Backed by leading Silicon Valley investors"
                ]
            },
            {
                "title": "Market Opportunity: $50B+ Enterprise AI",
                "subtitle": "Legacy RPA systems fail under non-deterministic workloads.",
                "bullets": [
                    "Global enterprise automation spending growing at 32% CAGR",
                    "78% of Fortune 500 deploying autonomous agent trials",
                    "High demand for automated video & document processing",
                    "Massive expansion opportunity in global developer tools"
                ]
            },
            {
                "title": "Product Traction & 10x ROI",
                "subtitle": "Rapid customer adoption across fintech, healthtech, and media.",
                "bullets": [
                    "Over 120 enterprise customers onboarded in Q2",
                    "340% YoY ARR growth with 135% net retention",
                    "Average customer saves 40+ hours per week per engineer",
                    "Key strategic partnerships with top tier cloud providers"
                ]
            },
            {
                "title": "Join the Revolution with Nexus AI",
                "subtitle": "Scaling the future of human and AI collaboration.",
                "bullets": [
                    "Raising $10M Series A to expand core engineering team",
                    "Accelerating international go-to-market execution",
                    "Building open developer ecosystem and integrations",
                    "Contact Founders: founders@nexusai.io"
                ]
            }
        ],
        accent_color=(37, 99, 235) # Blue accent
    )

    # Deck 2: SaaS Walkthrough
    generate_video(
        "samples/saas_walkthrough_deck.mp4",
        [
            {
                "title": "FlowHQ — All-in-One Workflow Automation",
                "subtitle": "Simplify complex business processes with zero code.",
                "bullets": [
                    "Drag-and-drop workflow builder for non-technical teams",
                    "Instant integrations with Slack, HubSpot, Jira, and Notion",
                    "Real-time analytics dashboard & task tracking",
                    "Automated trigger execution and webhooks"
                ]
            },
            {
                "title": "Key Feature 1: Intelligent Triggers",
                "subtitle": "Trigger actions based on real-time events and data updates.",
                "bullets": [
                    "Custom conditions and multi-branch logic support",
                    "Built-in data validation and schema transformation",
                    "Instant error handling and automatic retry queue",
                    "Custom notification routing across team channels"
                ]
            },
            {
                "title": "Key Feature 2: Automated Media Generation",
                "subtitle": "Convert raw documents into presentation videos.",
                "bullets": [
                    "AI voiceover synthesis for video announcements",
                    "Automated captioning and multi-language translation",
                    "Branded video templates and export options",
                    "1-click sharing to social channels and email newsletters"
                ]
            },
            {
                "title": "Get Started Free with FlowHQ Today",
                "subtitle": "Start automating your business in under 5 minutes.",
                "bullets": [
                    "Free 14-day trial with full feature access",
                    "No credit card required for initial setup",
                    "24/7 dedicated customer success support",
                    "Visit FlowHQ.com to claim your account"
                ]
            }
        ],
        accent_color=(5, 150, 105) # Emerald accent
    )
