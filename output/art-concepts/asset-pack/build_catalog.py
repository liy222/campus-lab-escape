"""Read-only image inspection and local gallery writer; never edits image bytes."""
from pathlib import Path
import argparse
import datetime
import hashlib
import html
import json
import struct
import xml.etree.ElementTree as ET
import zlib

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
REUSE = {
    'room1/r1_background.png', 'room2/r2_background_dark.png',
    'room2/r2_light_overlay_on.png', 'room3/r3_background.png',
}


def png_info(path):
    data = path.read_bytes()
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('Invalid PNG signature')
    offset = 8
    chunks = []
    while offset < len(data):
        size = struct.unpack('>I', data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8]
        body = data[offset + 8:offset + 8 + size]
        crc = struct.unpack('>I', data[offset + 8 + size:offset + 12 + size])[0]
        if zlib.crc32(kind + body) & 0xffffffff != crc:
            raise ValueError('PNG chunk checksum mismatch')
        chunks.append(kind.decode('ascii'))
        offset += size + 12
        if kind == b'IEND':
            break
    if 'IHDR' not in chunks or 'IDAT' not in chunks or chunks[-1] != 'IEND':
        raise ValueError('Incomplete PNG')
    width, height, depth, color = struct.unpack('>IIBB', data[16:26])
    info = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
            'width': width, 'height': height, 'bit_depth': depth,
            'png_color_type': color, 'alpha_channel_present': color in (4, 6) or 'tRNS' in chunks}
    try:
        from PIL import Image
        with Image.open(path) as im:
            im.verify()
        with Image.open(path) as im:
            info['decoded_mode'] = im.mode
            if im.mode in ('RGBA', 'LA'):
                info['alpha_range'] = list(im.getchannel('A').getextrema())
    except ImportError:
        info['decoded_validation'] = 'Pillow unavailable; PNG chunk integrity only'
    return info


def title_of(name):
    try:
        node = ET.parse(PROJECT / 'frontend/src/assets' / name).getroot()
        title = node.find('{http://www.w3.org/2000/svg}title')
        return title.text if title is not None and title.text else name.removesuffix('.svg')
    except ET.ParseError:
        return name.removesuffix('.svg')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--final', action='store_true')
    args = parser.parse_args()
    plan = json.loads((ROOT / 'plan.json').read_text(encoding='utf-8'))
    entries, missing = [], []
    for room, names in plan['source_assets'].items():
        for name in names:
            rel = room + '/' + name.removesuffix('.svg') + '.png'
            path = ROOT / rel
            entry = {'room': room, 'source_svg': name, 'image': rel,
                     'title': title_of(name), 'origin': 'reused scene study' if rel in REUSE else 'new generated object/state study',
                     'available': path.exists(), 'kind': 'closeup' if 'closeup' in name or name in ('microscope_view.svg', 'photo_closeup.svg') else 'object/state'}
            if path.exists():
                entry.update(png_info(path))
            else:
                missing.append(rel)
            entries.append(entry)
    backgrounds = []
    for image in sorted((ROOT / 'backgrounds').glob('*.png')):
        backgrounds.append({'image': image.relative_to(ROOT).as_posix(), **png_info(image)})
    catalog = {'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'status': 'complete image inventory' if not missing else 'in progress',
               'requested_source_count': len(entries), 'available_source_count': len(entries) - len(missing),
               'missing': missing, 'entries': entries, 'clean_backgrounds': backgrounds,
               'limitations': ['Art package only; not installed in the game.',
                               'Precise gameplay text, diagrams and device symbols need controlled runtime layers.',
                               'Generated geometry is not certified pixel-perfect across states.',
                               'R3 wood-and-metal door cutouts differ from the metal door in the earlier full-scene study.',
                               'r2_light_overlay_on is a reused full-scene study, not a transparent lighting overlay.']}
    (ROOT / 'catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    payload = json.dumps(catalog, ensure_ascii=False).replace('<', '\\u003c')
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>实验室手绘素材预览</title>
<style>body{margin:0;background:#172026;color:#eee9dd;font:16px/1.5 system-ui}header{padding:24px;position:sticky;top:0;background:#172026ee;z-index:1}h1{margin:0;font-size:24px}p{margin:8px 0;color:#c2c5be}nav{display:flex;gap:8px;flex-wrap:wrap}button,input{padding:10px 14px;border:1px solid #596665;border-radius:6px;background:#293836;color:inherit;font:inherit}button.active{background:#596954}main{padding:16px 24px;display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px}article{background:#27322f;border-radius:8px;overflow:hidden}a{color:#d9dbb7}figure{margin:0;display:grid;place-items:center;aspect-ratio:16/10;background:repeating-conic-gradient(#39453f 0% 25%,#455148 0% 50%) 50%/24px 24px}img{width:100%;height:100%;object-fit:contain;max-height:360px}section{padding:14px}small{display:block;color:#b4bcb4;overflow-wrap:anywhere}.pending{color:#d9b683}dialog{background:#1d2927;color:inherit;border:1px solid #89917c;max-width:94vw;max-height:94vh}dialog::backdrop{background:#000c}dialog img{width:85vw;height:75vh;max-height:none}#empty{padding:25px}</style>
<header><h1>实验室手绘素材预览</h1><p id="count"></p><p>独立美术素材包，尚未替换游戏画面。点击图片查看原图；棋盘、文字和符号仍需与正式玩法对齐。</p><nav><button data-room="all" class="active">全部</button><button data-room="room1">准备室</button><button data-room="room2">设备实验室</button><button data-room="room3">控制室</button><button data-room="backgrounds">分层背景</button><input id="search" type="search" placeholder="搜索物品或状态" aria-label="搜索素材"></nav></header><main id="grid"></main><dialog id="viewer"><button id="close">关闭预览</button><img id="large" alt=""><p id="caption"></p></dialog>
<script>const CATALOG=__DATA__;let room='all';const grid=document.getElementById('grid');const viewer=document.getElementById('viewer');function render(){const query=document.getElementById('search').value.toLowerCase();grid.replaceChildren();document.getElementById('count').textContent=`已保存 ${CATALOG.available_source_count} / ${CATALOG.requested_source_count} 个对应素材，另有 ${CATALOG.clean_backgrounds.length} 张独立分层背景。`;const list=room==='backgrounds'?CATALOG.clean_backgrounds.map(e=>({...e,title:e.image,available:true,room:'backgrounds'})):CATALOG.entries.filter(e=>room==='all'||e.room===room);for(const e of list.filter(e=>(e.title+' '+e.image).toLowerCase().includes(query))){const card=document.createElement('article');const fig=document.createElement('figure');if(e.available){const link=document.createElement('a');link.href=e.image;link.onclick=ev=>{ev.preventDefault();document.getElementById('large').src=e.image;document.getElementById('large').alt=e.title;document.getElementById('caption').textContent=e.title+' · '+e.image;viewer.showModal()};const im=document.createElement('img');im.src=e.image;im.alt=e.title;im.loading='lazy';link.append(im);fig.append(link)}else{fig.textContent='尚未生成';fig.className='pending'}const text=document.createElement('section');const title=document.createElement('strong');title.textContent=e.title;const file=document.createElement('small');file.textContent=e.image;const meta=document.createElement('small');meta.textContent=e.available?`${e.width} × ${e.height} · ${(e.bytes/1048576).toFixed(2)} MB`:'制作中';text.append(title,file,meta);card.append(fig,text);grid.append(card)}}document.querySelectorAll('[data-room]').forEach(b=>b.onclick=()=>{room=b.dataset.room;document.querySelectorAll('[data-room]').forEach(x=>x.classList.toggle('active',x===b));render()});document.getElementById('search').oninput=render;document.getElementById('close').onclick=()=>viewer.close();render();</script></html>'''
    (ROOT / 'index.html').write_text(page.replace('__DATA__', payload), encoding='utf-8')
    print(json.dumps({'available': len(entries) - len(missing), 'requested': len(entries), 'backgrounds': len(backgrounds), 'missing': len(missing)}, ensure_ascii=False))
    if args.final and missing:
        raise SystemExit('Final inventory has missing images')


if __name__ == '__main__':
    main()
