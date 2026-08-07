import os
import cv2
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def create_slide_img(title: str, subtitle: str, bullets: list, bg_color=(255, 255, 255), text_color=(15, 23, 42), accent_color=(255, 90, 95), width=1280, height=720) -> Image.Image:
    """Draw a clean presentation slide image."""
    image = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(image)
    
    try:
        font_title = ImageFont.truetype("arial.ttf", 44)
        font_sub = ImageFont.truetype("arial.ttf", 26)
        font_bullet = ImageFont.truetype("arial.ttf", 22)
    except Exception:
        font_title = font_sub = font_bullet = ImageFont.load_default()

    # Top accent bar (Airbnb Pink #FF5A5F)
    draw.rectangle([60, 50, width - 60, 56], fill=accent_color)
    
    # Brand tag
    draw.text((60, 75), "AIRBNB · ORIGINAL 2009 SEED PITCH DECK", font=font_sub, fill=(100, 116, 139))

    # Title
    draw.text((60, 125), title, font=font_title, fill=text_color)
    
    # Subtitle
    draw.text((60, 190), subtitle, font=font_sub, fill=(71, 85, 105))

    # Card container
    card_top = 250
    card_bottom = height - 70
    draw.rectangle([60, card_top, width - 60, card_bottom], fill=(248, 250, 252), outline=(226, 232, 240), width=2)

    y_pos = card_top + 40
    for bullet in bullets:
        draw.ellipse([90, y_pos + 8, 102, y_pos + 20], fill=accent_color)
        draw.text((120, y_pos), bullet, font=font_bullet, fill=(30, 41, 59))
        y_pos += 50

    return image

def generate_pdf_pitch_deck(output_pdf_path: str = "samples/airbnb_seed_deck.pdf"):
    out_dir = Path(output_pdf_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    slides = [
        {
            "title": "AirBed & Breakfast (Airbnb)",
            "subtitle": "Book rooms with locals, rather than hotels.",
            "bullets": [
                "Save money when traveling by staying with local hosts",
                "Make money by renting out extra space in your home",
                "Experience local culture and authentic community travel",
                "Search by price, location, and host reviews"
            ]
        },
        {
            "title": "The Problem in Travel Accommodations",
            "subtitle": "Price is a major concern for travelers online.",
            "bullets": [
                "Hotels leave you disconnected from the city and culture",
                "No easy way exists to book a room with a local or host",
                "Hotels are expensive and often overbooked during events",
                "Homeowners have no safe way to monetize spare bedrooms"
            ]
        },
        {
            "title": "The Solution: A Web Marketplace",
            "subtitle": "A web platform where users can rent out space to travelers.",
            "bullets": [
                "Save Money: Affordable alternative to expensive hotels",
                "Make Money: Hosts earn extra income from extra space",
                "Local Culture: Authentic local experience for travelers",
                "Verified Profiles: Peer reviews and secure payments"
            ]
        },
        {
            "title": "Market Validation & Opportunity",
            "subtitle": "630,000+ total couchsurfing users & massive TAM.",
            "bullets": [
                "1.9 Billion+ global budget travel trips booked per year",
                "560 Million+ target addressable budget & peer travel market",
                "10.6 Million+ estimated market share at 15% adoption",
                "Revenue Model: 10% commission on every transaction"
            ]
        }
    ]

    pil_images = []
    for s in slides:
        img = create_slide_img(s["title"], s["subtitle"], s["bullets"])
        pil_images.append(img)

    # Save as multi-page PDF
    if pil_images:
        pil_images[0].save(output_pdf_path, save_all=True, append_images=pil_images[1:])
        print(f"Generated sample PDF pitch deck at: {output_pdf_path}")

if __name__ == "__main__":
    generate_pdf_pitch_deck()
