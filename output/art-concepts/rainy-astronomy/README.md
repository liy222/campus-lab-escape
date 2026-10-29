当前默认已切换至[手绘重建版1.1.0](handpainted-v2/README.md)。以下为原矢量版1.0.0的历史制作记录，保留来源，不代表当前美术制作方式。

# 雨夜天文社主题包：制作与接入说明

本目录保存 `rainy-astronomy` 主题包的源文件、构建脚本和成品清单。成品图片在 `frontend/public/art-themes/rainy-astronomy/`，前端描述在 `frontend/src/assets/themes/rainy-astronomy/manifest.json`。

## 实际制作方式（重要）

- 本阶段没有可用的图像生成模型或 imagegen 技能，因此**没有使用 AI 生图**，也没有调用任何外部付费服务。
- 全部画面是**手写矢量插画**：Python 组合 SVG（渐变、蒙版、噪点颗粒、手绘路径），再用本机 **headless Chrome 截图为 PNG**，Pillow 记录真实像素尺寸、裁掉透明边并写入 manifest。
- 因此风格是“干净矢量 + 纸面颗粒”，不是早前手绘包的水彩质感；这一点在阶段复核里如实记为局限，没有把它说成手绘或模型生成。

## 目录

```text
output/art-concepts/rainy-astronomy/
  ART-DIRECTION.md        设计依据（配色、字号、布局、角色、回退）
  ASSET-LIST.md           按成品生成的实际清单（尺寸/大小/路径）
  build-report.json       最近一次构建时间与产物列表
  source/
    artlib.py             SVG 基础件（窗、雨、木、纸、星图、颗粒滤镜）
    scenes.py             三张 1600×900 背景 + 八个槽位落点
    objects.py            六类物件、12 种外观/状态
    build.py              渲染 + 裁切 + 写 manifest
    asset_report.py       生成 ASSET-LIST.md
    svg/                  每次构建保存的 SVG 源（可重放）
frontend/public/art-themes/rainy-astronomy/
  backgrounds/  objects/  closeups/
frontend/src/assets/themes/rainy-astronomy/manifest.json
```

## 重建

```powershell
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B -X utf8 -c "import sys; sys.path.insert(0,'output/art-concepts/rainy-astronomy'); import source.build as b; b.build()"
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B -X utf8 -c "import sys; sys.path.insert(0,'output/art-concepts/rainy-astronomy'); from source import asset_report; asset_report.main()"
```

构建是确定性的：同一份 `source/` 重新渲染得到同样的构图与尺寸。渲染依赖本机 Chrome/Edge，不需要网络。

## 接入方式

- 前端只读 `manifest.json`（约 12 KB），图片按房间/物件在 Phaser 里按需加载，不在启动时预载整个包。
- 主题以**已保存的 `level.theme`** 匹配（`frontend/src/v5/visual/registry.ts`），匹配失败回退通用素材。
- 物件外观按公开 `art_id` + `completed` + 稳定哈希选择；资料纸面额外参考公开物件名称。渲染层不回写 `revision/definition_hash`，也不改服务端 ID。
- 旧 `frontend/src/assets/generated-catalog.json` 与经典页面保持原样，仍作为回退与经典关卡使用。

## 已知限制

- 只有天文社这一包；其他主题仍用通用手绘素材（创建页会提示）。
- 背景是 1.5 MB 级 PNG（未做有损压缩），本地服务直接读磁盘，首次进入房间会有一两秒加载；没有为体积牺牲清晰度。
- 图中装饰性符号、星图连线不构成谜题答案。
