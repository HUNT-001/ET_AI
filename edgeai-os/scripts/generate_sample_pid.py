"""
Generates a clean synthetic P&ID-style drawing (PNG) for testing the
VisionAgent pipeline: two circular pump/instrument symbols, a rectangular
vessel, connecting pipe lines, and printed equipment tags (P-101A, V-204,
T-300) that OCR should recover.
"""

import os

from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(__file__), "..", "datasets", "samples", "sample_pid.png")

W, H = 1400, 900
img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)

try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
    small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
except Exception:
    font = ImageFont.load_default()
    small = font

BLACK = (10, 10, 10)
LW = 5

# Pump P-101A: circle + tag
d.ellipse([150, 380, 310, 540], outline=BLACK, width=LW)
d.text((165, 545), "P-101A", fill=BLACK, font=font)

# Instrument bubble (circle) near the vessel
d.ellipse([640, 180, 740, 280], outline=BLACK, width=LW)
d.text((648, 285), "PI-12", fill=BLACK, font=small)

# Vessel T-300: rectangle
d.rectangle([620, 360, 860, 700], outline=BLACK, width=LW)
d.text((680, 705), "T-300", fill=BLACK, font=font)

# Valve V-204: bowtie between pump and vessel + tag
d.polygon([(450, 430), (520, 470), (450, 510)], outline=BLACK, width=LW)
d.polygon([(590, 430), (520, 470), (590, 510)], outline=BLACK, width=LW)
d.text((455, 520), "V-204", fill=BLACK, font=font)

# Piping lines
d.line([310, 460, 450, 460], fill=BLACK, width=LW)     # pump -> valve
d.line([590, 470, 620, 470], fill=BLACK, width=LW)     # valve -> vessel
d.line([860, 530, 1150, 530], fill=BLACK, width=LW)    # vessel -> outlet
d.line([1150, 530, 1150, 250], fill=BLACK, width=LW)   # riser
d.line([740, 230, 1150, 230], fill=BLACK, width=LW)    # instrument line

# Title block
d.rectangle([1000, 760, 1380, 880], outline=BLACK, width=3)
d.text((1015, 775), "UNIT 3 — SIMPLIFIED P&ID", fill=BLACK, font=small)
d.text((1015, 815), "DWG-PID-0007  Rev B", fill=BLACK, font=small)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
img.save(OUT)
print("wrote", OUT)
