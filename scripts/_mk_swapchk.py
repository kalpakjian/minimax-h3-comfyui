from PIL import Image, ImageDraw

files = [
    (r"C:\Users\princ\swapchk_src.png", "SOURCE"),
    (r"C:\Users\princ\swapchk_nocc.png", "SWAP no CC"),
    (r"C:\Users\princ\swapchk_swap.png", "SWAP + CC (final)"),
]
imgs = [Image.open(p).convert("RGB") for p, _ in files]
w, h = imgs[0].size
lab = 40
canvas = Image.new("RGB", (w * 3, h + lab), "black")
d = ImageDraw.Draw(canvas)
for x, img, s in zip((0, w, 2 * w), imgs, [s for _, s in files]):
    canvas.paste(img, (x, lab))
    d.text((x + 10, 12), s, fill=(255, 220, 0))
canvas.save(r"C:\Users\princ\swapchk_3panel.png")
print("saved", canvas.size)
