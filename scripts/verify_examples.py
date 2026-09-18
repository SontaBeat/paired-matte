"""Check example integrity, dimensions, alpha modes and downloadable outputs."""
from pathlib import Path
import hashlib
import json
from PIL import Image
root = Path(__file__).resolve().parents[1]
for manifest_file in sorted((root / 'examples').glob('*/manifest.json')):
    folder = manifest_file.parent
    meta = json.loads(manifest_file.read_text())
    size = (meta['size']['width'], meta['size']['height'])
    for name, digest in meta['sha256'].items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest, f'{folder.name}/{name}: hash mismatch'
    with Image.open(folder / 'alpha.png') as mask, Image.open(folder / 'solid.png') as solid, Image.open(folder / 'cutout.png') as cutout:
        assert mask.mode == 'L' and cutout.mode == 'RGBA'
        assert mask.size == solid.size == cutout.size == size
        assert 0 < mask.histogram()[0] < size[0]*size[1]
        a = cutout.getchannel('A').histogram()
        assert a[0] > 0 and a[255] > 0 and sum(a[1:255]) > 0
        rgb_bytes = solid.convert('RGB').tobytes()
        assert all(rgb_bytes[i*3:i*3+3] == bytes((128,128,128)) for i, value in enumerate(mask.tobytes()) if value == 0)
        # A diagnostic overlay accidentally exported as PNG would fail alpha checks above.
        for bg in ['black', 'white']:
            with Image.open(folder / f'preview-{bg}.png') as preview:
                assert preview.size == size and preview.mode == 'RGB'
    print(f'PASS {folder.name}: hashes, dimensions, L mask, solid background, RGBA and previews')
