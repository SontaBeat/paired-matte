"""Copy an explicitly supplied pair into a portable example, stripping metadata."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--id', required=True, choices=['veil-warrior', 'silver-swordsman', 'magic-duo', 'blonde-portrait', 'pearl-gauze'])
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--solid', type=Path, required=True)
parser.add_argument('--alpha', type=Path, required=True)
parser.add_argument('--route', required=True, choices=['builtin', 'web-solid-builtin-mask', 'web'])
parser.add_argument('--cutout', type=Path, help='Existing verified web export; copy pixels without recomputing alpha.')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
dest = root / 'examples' / args.id
dest.mkdir(parents=True, exist_ok=True)
if (dest / 'manifest.json').exists():
    raise SystemExit('Example already exists; keep historical inputs unchanged.')
files = {}
size = None
inputs = [('source.png', args.source), ('solid.png', args.solid), ('alpha.png', args.alpha)]
if args.cutout:
    inputs.append(('cutout.png', args.cutout))
for name, source in inputs:
    with Image.open(source) as image:
        if size is None:
            size = image.size
        if image.size != size:
            raise SystemExit('Historical source and pair dimensions do not match.')
        if name == 'cutout.png' and image.mode != 'RGBA':
            raise SystemExit('Expected an RGBA web export.')
        normalized = image.convert('L' if name == 'alpha.png' else 'RGBA' if name == 'cutout.png' else 'RGB')
        clean = Image.new(normalized.mode, normalized.size)
        clean.paste(normalized)
        clean.save(dest / name, optimize=True)
    files[name] = hashlib.sha256((dest / name).read_bytes()).hexdigest()
manifest = {
    'id': args.id, 'size': {'width': size[0], 'height': size[1]},
    'background': '#808080', 'historical_generation_route': args.route,
    'provenance': 'Author-provided historical AI artwork and accepted paired outputs; no ground-truth alpha.',
    'cutout_provenance': 'Re-exported with the draft web tool; see settings.json.',
    'web_end_to_end_rerun': args.route == 'web', 'artwork_license': 'Author-created demonstration assets; excluded from code GPL; see ../ASSETS.md.',
    'sha256': files,
}
if args.route == 'web':
    manifest.update({
        'generation_route': 'ChatGPT website in Safari: source to solid, re-upload solid to generate mask.',
        'provenance': 'Author-provided images processed on 2026-09-17; no ground-truth alpha or verified camera provenance.',
        'cutout_provenance': 'Existing Safari export from the local draft web tool, copied without pixel changes; see settings.json.',
        'validation': 'Raw-solid contour overlay and black/white composites inspected; no obvious global shift. Not a pixel-perfect or true-alpha guarantee.',
        'export_alpha_max_difference_255': 2,
    })
(dest / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
print(f'Prepared {args.id}: {size[0]}x{size[1]}')
