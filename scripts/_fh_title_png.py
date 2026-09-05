# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw, ImageFont, ImageFilter
TITLE = "\u70fd\u706b\u908a\u95dc"
FONT_PATH = r"C:\Windows\Fonts\kaiu.ttf"
W, H = 1344, 768
FS = 172
OUT_PNG = r"C:\minimax+comfyUI\output\video\_fh_title.png"
OUT_CHK = r"C:\minimax+comfyUI\logs\_fh_title_gold_check.png"
# Build solid gold text via layered draws
base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
font = ImageFont.truetype(FONT_PATH, FS)
# measure
tmp = ImageDraw.Draw(base)
bb = tmp.textbbox((0, 0), TITLE, font=font, stroke_width=0)
tw, th = bb[2] - bb[0], bb[3] - bb[1]
x = (W - tw) // 2 - bb[0]
y = (H - th) // 2 + 24 - bb[1]
# 1) blurred black shadow
sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(sh).text((x+4, y+6), TITLE, font=font, fill=(0,0,0,255), stroke_width=14, stroke_fill=(0,0,0,255))
sh = sh.filter(ImageFilter.GaussianBlur(10))
base = Image.alpha_composite(base, sh)
# 2) dark outer ring (no fill - use stroke only by drawing fill same as transparent trick: draw full then punch? just thick dark)
layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(layer).text((x, y), TITLE, font=font, fill=(20,12,4,255), stroke_width=14, stroke_fill=(20,12,4,255))
base = Image.alpha_composite(base, layer)
# 3) bronze mid ring
layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(layer).text((x, y), TITLE, font=font, fill=(160,96,20,255), stroke_width=8, stroke_fill=(160,96,20,255))
base = Image.alpha_composite(base, layer)
# 4) solid bright gold body (fill + thin stroke same color)
layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(layer).text((x, y), TITLE, font=font, fill=(255, 210, 90, 255), stroke_width=3, stroke_fill=(255, 190, 60, 255))
base = Image.alpha_composite(base, layer)
# 5) top-left highlight wash
layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(layer).text((x-1, y-2), TITLE, font=font, fill=(255, 245, 200, 90), stroke_width=0)
base = Image.alpha_composite(base, layer)
base.save(OUT_PNG)
comp = Image.new("RGBA", (W, H), (10, 8, 6, 255))
comp.alpha_composite(base)
comp.convert("RGB").save(OUT_CHK)
# also save on mid-tone sand to judge contrast
comp2 = Image.new("RGBA", (W, H), (160, 120, 70, 255))
comp2.alpha_composite(base)
comp2.convert("RGB").save(r"C:\minimax+comfyUI\logs\_fh_title_sand_check.png")
print("TITLE_PNG_OK solid-gold FS=", FS, "tw=", tw, "th=", th)
