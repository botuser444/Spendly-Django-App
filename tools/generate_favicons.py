from PIL import Image
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
src = BASE / 'static' / 'images' / 'spendly-logo.png'
if not src.exists():
    src = BASE / 'budget' / 'static' / 'images' / 'spendly-logo.png'
    if not src.exists():
        raise SystemExit(f"Source logo not found at expected paths: {src}")

sizes = [48, 96, 192, 512]
out_dir = BASE / 'static' / 'images'
out_dir.mkdir(parents=True, exist_ok=True)

for s in sizes:
    img = Image.open(src).convert('RGBA')
    # Resize preserving aspect ratio, and fit into square
    img.thumbnail((s, s), Image.LANCZOS)
    # create square canvas and paste centered
    canvas = Image.new('RGBA', (s, s), (0,0,0,0))
    x = (s - img.width) // 2
    y = (s - img.height) // 2
    canvas.paste(img, (x, y), img)
    out_path = out_dir / f'spendly-favicon-{s}.png'
    canvas.save(out_path)
    # also write to app static for app finder
    app_out = BASE / 'budget' / 'static' / 'images' / f'spendly-favicon-{s}.png'
    app_out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(app_out)
    print('Wrote', out_path)

print('All favicons generated.')
