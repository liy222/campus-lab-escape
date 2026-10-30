"""Render the offline-safe art catalogue from current theme manifests."""
from pathlib import Path
from html import escape
import json

ROOT = Path(__file__).resolve().parents[3]
THEMES = ('rainy-astronomy', 'library-archive', 'chemistry-lab', 'computer-room', 'campus-broadcast')
ROLE = {'note':'纸本资料', 'key':'黄铜钥匙', 'terminal':'终端', 'cabinet':'储物柜', 'circuit':'配电设备', 'panel':'按钮面板'}
BASE = {'neutral_lab':'前厅与活动室', 'neutral_archive':'资料准备室', 'neutral_control':'控制与工作室'}
STATE = {'default':'初始状态', 'completed':'完成状态'}
cards = []
def card(src, caption, bg=False):
    relative = src.removeprefix('/art-themes/')
    assert not relative.startswith('/') and '..' not in Path(relative).parts
    cards.append(relative)
    return f'<figure class="{"background" if bg else "prop"}"><a href="{escape(relative)}" target="_blank"><img src="{escape(relative)}" alt="{escape(caption)}" loading="lazy"></a><figcaption>{escape(caption)}</figcaption></figure>'

sections=[]
packs=[]
for theme in THEMES:
    pack=json.loads((ROOT/'frontend/src/assets/themes'/theme/'manifest.json').read_text(encoding='utf-8'))
    packs.append(pack)
    content=[]
    for base, candidates in pack['background_variants'].items():
        for item in candidates:
            content.append(card(item['background']['src'], BASE[base]+' · '+('新增布局' if item.get('available_from') else '原布局'), True))
    content.append('</div><h3>主题资料与终端</h3><div class="grid props">')
    for role in ('note','terminal'):
        for variant in pack['objects'][role].values():
            label=ROLE[role]+' · '+STATE[variant['state']]+' · '+('新增外观' if variant.get('available_from') else '原外观')
            content.append(card(variant['src'],label))
    sections.append(f'<section id="{theme}"><h2>{escape(pack["display_name"])}</h2><p>三类房间各有两种背景布局。资料按类型选择，终端按同一外观切换状态。</p><div class="grid">'+''.join(content)+'</div></section>')

shared=[]
for role in ('key','cabinet','circuit','panel'):
    for variant in packs[0]['objects'][role].values():
        shared.append(card(variant['src'],ROLE[role]+' · '+STATE[variant['state']]+' · '+('新增外观' if variant.get('available_from') else '原外观')))
sections.append('<section id="shared"><h2>五类主题共用物件</h2><p>这里每张原图只展示一次；设备的初始与完成图属于同一款外观。</p><div class="grid props">'+''.join(shared)+'</div></section>')
assert len(cards)==86 and len(set(cards))==74, (len(cards),len(set(cards)))
nav=''.join(f'<a href="#{p["theme_id"]}">{escape(p["display_name"])}</a>' for p in packs)+'<a href="#shared">共用物件</a>'
html='''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>逃离校园实验室 · 主题美术图集</title>
<style>
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;min-width:1080px;background:#182e29;color:#eee6cf;font:16px/1.7 "Microsoft YaHei",sans-serif}main{width:min(1560px,94%);margin:48px auto}header{padding:30px;border:1px solid #637368;background:#223b33}h1{font-size:34px;margin:0 0 16px;color:#e6c17d}h2{font-size:28px;color:#e6c17d;margin-bottom:8px}h3{font-size:20px;margin-top:28px}p{margin:8px 0;color:#cfcebd}nav{display:flex;gap:14px;flex-wrap:wrap;margin-top:22px}a{color:#e6c17d}nav a{padding:7px 14px;border:1px solid #6d7963;text-decoration:none}section{padding-top:34px;scroll-margin-top:20px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px}.props{grid-template-columns:repeat(4,minmax(0,1fr))}figure{margin:0;border:1px solid #5b6a5c;background:#283c34}figure a{display:block;background:#d6d0ba}img{display:block;width:100%;height:260px;object-fit:contain}.background img{height:auto;aspect-ratio:16/9;object-fit:cover}.prop a{background:repeating-conic-gradient(#c9c8b7 0% 25%,#d9d7c7 0% 50%) 0/24px 24px}figcaption{padding:12px;font-size:14px}footer{margin-top:40px;border-top:1px solid #65745f;padding:24px 0}
</style></head><body><main><header><p>逃离校园实验室 / 美术素材库</p><h1>五类主题，更多场景搭配</h1><p>本轮新增 31 张原图：15 张背景、8 张资料与钥匙、8 张设备状态。累计 74 张独立原图。</p><p>本页共 86 个展示卡片；共用资料和设备可能重复出现。点击图片可看原图，所有图片均可从本地直接打开。</p><p>新关卡会稳定选用背景与物件外观，刷新和读档不变；已有旧关卡保留原外观。组合有限，连续生成仍可能重复。尚未真人验收。</p><nav>'''+nav+'</nav></header>'+''.join(sections)+'''<footer><a href="http://127.0.0.1:8001/">进入游戏（需先启动本地服务）</a><p>本图集只展示美术，不调用生成模型。美术中的空白纸面与屏幕不包含谜题答案。</p></footer></main></body></html>
'''
(ROOT/'frontend/public/art-themes/campus-theme-library.html').write_text(html,encoding='utf-8')
print(json.dumps({'gallery_cards':len(cards),'unique_source_images':len(set(cards))}))
