"""Build static comparison images and a local review page from web-exported PNGs."""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[1]
titles = {'veil-warrior': '白纱女剑士', 'silver-swordsman': '白发男剑士', 'magic-duo': '双人法器与烟雾', 'blonde-portrait': '写实金发人物', 'pearl-gauze': '珍珠白半透明纱物'}
cards = []
for key, title in titles.items():
    folder = root / 'examples' / key
    with Image.open(folder / 'cutout.png') as image:
        cutout = image.convert('RGBA')
    for name, color in [('black', (17, 17, 17, 255)), ('white', (255, 255, 255, 255))]:
        Image.alpha_composite(Image.new('RGBA', cutout.size, color), cutout).convert('RGB').save(folder / f'preview-{name}.png')
    names = [('source.png', 'SOURCE'), ('solid.png', 'SOLID #808080'), ('alpha.png', 'ALPHA'), ('preview-black.png', 'ON DARK'), ('preview-white.png', 'ON WHITE')]
    sheet = Image.new('RGB', (1600, 560), (239, 241, 240))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=16)
    for i, (filename, label) in enumerate(names):
        draw.text((i*320+16, 16), label, fill=(28, 36, 35), font=font)
        with Image.open(folder / filename) as source:
            thumb = source.convert('RGB')
            thumb.thumbnail((304, 508), Image.Resampling.LANCZOS)
            sheet.paste(thumb, (i*320+(320-thumb.width)//2, 42+(508-thumb.height)//2))
    sheet.save(folder / 'comparison.jpg', quality=92)
    manifest_path = folder / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    for name in ['cutout.png', 'preview-black.png', 'preview-white.png', 'comparison.jpg', 'settings.json']:
        manifest['sha256'][name] = hashlib.sha256((folder / name).read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    size = manifest['size']
    route = '2026-09-17 网页版生成配对图，Safari 本地工具导出' if manifest.get('web_end_to_end_rerun') else '历史配对图，网页重新导出'
    cards.append(f'''<section><h2>{title}</h2><p>{size['width']} × {size['height']} · {route}</p><img src="examples/{key}/comparison.jpg" alt="{title} 原图、纯色图、遮罩及黑白底结果"><p><a href="examples/{key}/README.md">案例说明</a> · <a href="examples/{key}/source.png">原图</a> · <a href="examples/{key}/solid.png">纯色图</a> · <a href="examples/{key}/alpha.png">遮罩</a> · <a href="examples/{key}/cutout.png">透明 PNG</a></p></section>''')
html = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Paired Matte · 演示总览</title><style>body{margin:0;background:#f3f5f2;color:#20322f;font:16px/1.8 system-ui,-apple-system,sans-serif}main{max-width:1300px;margin:0 auto;padding:44px 24px}header,section{background:white;border:1px solid #d9e2db;border-radius:14px;padding:28px;margin-bottom:22px}h1{font-size:36px;line-height:1.2}h2{font-size:23px}a{color:#006c72}img{width:100%;height:auto;border:1px solid #ddd}small{color:#56665f}.tag{display:inline-block;padding:3px 12px;background:#fff2d2;border-radius:12px}.flow{padding:18px;background:#edf5f1;border-radius:8px}nav{display:flex;gap:20px;flex-wrap:wrap}</style><main><header><span class="tag">配对遮罩 · 半透明抠图</span><h1>Paired Matte<br>配对遮罩半透明抠图</h1><p>ChatGPT 网页生图流程、可复制 Skill、本地网页与历史案例。</p><div class="flow">原图 → 纯色底图 → 以纯色图生成 Alpha → 对齐检查 → 去底色与微调 → 透明 PNG</div><p>三组演示可查看完整文件。模型 Alpha 没有真值；半透明与光效的质量需在目标背景下判断。</p><nav><a href="cutout-tool.html">打开网页工具</a><a href="README.zh-CN.md">中文 README</a><a href="REVIEW.md">质量检查清单</a><a href="skills/gpt-image-2-subject-assets/SKILL.md">查看 Skill</a></nav></header>''' + ''.join(cards) + '''<footer><small>代码、Skill 与文档采用 GPL-3.0-or-later；演示素材由作者制作并授权用于项目演示。</small></footer></main></html>'''
html = html.replace('本地网页与历史案例。', '本地网页、历史案例与新增网页版实测案例。').replace('三组演示可查看完整文件。', f'{len(cards)} 组演示可查看完整文件，其中两组为新增网页版流程实测。')
html = html.replace('<nav>', '<nav><a href="walkthrough.html">完整演示：准备图片 → 网页导出</a>', 1)
(root / 'review.html').write_text(html, encoding='utf-8')
print('Rendered comparisons, black/white previews and review.html')
