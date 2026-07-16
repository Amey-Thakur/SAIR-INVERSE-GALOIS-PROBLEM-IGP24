import urllib.request
import os
from PIL import Image, ImageDraw, ImageFont

# Download a nice monospace font (Roboto Mono)
url = "https://github.com/googlefonts/RobotoMono/raw/main/fonts/ttf/RobotoMono-Regular.ttf"
font_path = "RobotoMono-Regular.ttf"
if not os.path.exists(font_path):
    try:
        urllib.request.urlretrieve(url, font_path)
    except Exception as e:
        print(f"Failed to download font: {e}")

# Image dimensions (GitHub social preview size)
W, H = 1280, 640

# Colors (Monokai-ish IDE style)
bg_color = (30, 30, 30)
text_color = (212, 212, 212)
green = (181, 206, 168)
blue = (86, 156, 214)
yellow = (220, 220, 170)

img = Image.new('RGB', (W, H), color=bg_color)
d = ImageDraw.Draw(img)

# Load font
try:
    font_title = ImageFont.truetype(font_path, 50)
    font_body = ImageFont.truetype(font_path, 35)
except Exception:
    font_title = ImageFont.load_default()
    font_body = ImageFont.load_default()

# Draw title
d.text((80, 80), "SAIR Inverse Galois Problem (IGP24)", font=font_title, fill=blue)
d.text((80, 150), "==========================================================", font=font_body, fill=text_color)

body_text = """
def evaluate_candidate(coeffs: list[int]):
    print("[*] Analyzing monic polynomial of degree 24...")
    print("[*] Verifying transitive subgroup 24T_t signature...")
    
    discriminant = pari_wrapper.nfdisc(coeffs, timeout=60)
    
    if discriminant != "TIMEOUT":
        print("[SUCCESS] Exact absolute discriminant computed.")
        print(f"D = {discriminant}")
        return True
    return False

# Target: 24T_25000 (Mathieu M24)
"""
d.multiline_text((80, 220), body_text, font=font_body, fill=green, spacing=15)

img.save('social_preview.png')
print("Created social_preview.png using Pillow!")
