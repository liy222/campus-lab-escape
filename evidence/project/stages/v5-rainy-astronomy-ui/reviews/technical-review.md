# 技术复核（实施者自述，非独立复核、非真人验收）

阶段：`v5-rainy-astronomy-ui`。本文记录实施者本人对本次改动的技术复核：改了什么、怎么验证的、哪里还没验证。**这不是独立 QA，也不是用户验收。**

## 1. 改动范围

| 区域 | 文件 | 说明 |
|---|---|---|
| 主题描述与解析 | `frontend/src/v5/visual/{types.ts,registry.ts,scene.ts}` | 新类型、主题匹配（按已保存 `level.theme`）、稳定外观选择、槽位到场景的映射 |
| 场景渲染 | `frontend/src/v5/GeneratedScene.tsx` | 改为读取主题包；背景/物件按房间按需加载；热点来自同一份 `slot_layout` |
| 游戏界面 | `frontend/src/v5/GeneratedPlay.tsx` | HUD、场景脚注、物品栏、四类谜题面板、笔记/伙伴/存档、结算层；保留原有请求/状态/焦点逻辑 |
| 创建与登录 | `frontend/src/v5/Workspace.tsx` | 统一视觉、主题覆盖提示、关卡封面与主题标签、生成后列表延迟刷新 |
| 样式 | `frontend/src/v5/v5.css` | 全量重写为夜色/纸色/黄铜体系；44px 控件、三视口媒体查询 |
| 素材 | `frontend/public/art-themes/rainy-astronomy/**`、`frontend/src/assets/themes/rainy-astronomy/manifest.json` | 3 背景、12 物件外观、12 特写 |
| 素材源 | `output/art-concepts/rainy-astronomy/**` | SVG 源、构建脚本、清单、设计说明 |
| 检查 | `tests/v5/run_visual_ui_browser.mjs`、`tests/v5/visual_ui_fixture_server.py` | 隔离合成浏览器检查 |

未改动：`backend/**`、`contracts/**`、`evaluation/**`、`frontend/src/assets/generated-catalog.json`、旧 `art-handpainted` 素材、`App.tsx`/经典 Room 页面、`frontend/src/api.ts`、`frontend/src/v5/client.ts`。

## 2. 实际执行过的命令与结果

```powershell
# 类型检查（多次，最后一次在最终构建前）
cd frontend; npx tsc --noEmit                 # exit 0

# 构建
$env:VITE_GAMEPLAY_VERSION='v5'; $env:CAMPUS_BACKEND_URL='http://127.0.0.1:8001'
npm --prefix frontend run build               # exit 0

# 素材重建（多次）
python -B -X utf8 -c "...import source.build as b; b.build()"   # exit 0

# 隔离浏览器检查（共 21 次运行，15 失败保留）
node tests/v5/run_visual_ui_browser.mjs
# 最终：exit 0，36 项通过，17 张截图
# automated/browser-2026-10-28T16-20-30-946Z-97ce062e/browser-result.json
```

## 3. 检查覆盖了什么

- 主题包解析与背景替换、5 个物件的外观映射、钥匙不再用保险丝图、特写来源。
- 三个视口的 44px 最小控件与无横向溢出（1280×720 / 390×844 / 812×375）。
- 覆盖层：Escape 关闭、点背景不穿透、热点在面板打开时 disabled。
- 真实规则通关：公开线索推码 → 取钥匙 → 提交密码 → 用钥匙开柜 → 出口 → 服务端结算。
- 存档：保存新时刻、读取、删除；读取后状态与存档列表来自服务端响应。
- 刷新后外观稳定；未支持主题回退通用素材且写明；0 外部请求；8001 用户服务未被访问。

## 4. 独立只读复核（另一次会话，2026-10-29 00:17）

由一个独立子会话只读审查源码、manifest、检查脚本与最新结果，不修改文件、不跑构建。它指出（摘要）：

- **阻断**：完成态变体贴图从未加载——`draw()` 对缺失贴图直接 return，`preload` 只在挂载或换房间时执行，因此终端/资料柜完成后会从画面消失，而检查仍然全绿。
- **应修**：检查只看 `data-variant` 与 `state.objects.completed`，没有验证贴图、实际提交或错误恢复；只断言第一间房背景；稳定性链缺少“保存→推进→读取”；手机结算可能被 stage 裁切；通用回退里钥匙仍指向旧保险丝图；文档中的运行次数互不一致。
- **建议**：首屏加载 1.5MB 背景与“按房间加载”的说法冲突；`closeup_bbox` 未使用；面板焦点若被移除，Tab 可能离开 modal。
- **未审查**：真实模型生成的关卡画面、真人体验、真机触控、经典三房间页面回归。

## 5. 对独立复核的处理

| 复核意见 | 处理 |
|---|---|
| 阻断：完成态贴图未加载 | 已修。`buildSceneModel` 为当前房间的角色补出“其他状态”贴图（`extras`），`GeneratedScene` 一并预载；`draw()` 缺图时画占位方块而不是静默消失。新增断言：每个热点 variant 必须出现在 `.v5-scene` 的 `data-textures`，且 terminal-on / cabinet-open 必须已加载（`07-victory-scene.png` 可见完成态终端与开柜）。 |
| 检查未验证实际提交/贴图 | 部分修。新增贴图断言、手机结算几何断言、存档→推进→读取→重载链；线路/顺序的实际提交仍未在本轮补（见第 6 节）。 |
| 只断言第一间房 | 未修，保留为限制：3 房只走到第 2 间，第 3 间只有文件与映射证据。 |
| 手机结算可能被裁 | 已修。`.v5-victory` 加 `max-height:100%; overflow:auto`，手机下改为顶部对齐；新增 390×844 结算截图与“按钮在 stage 内”的断言。 |
| 通用回退钥匙仍是保险丝 | 已修。回退路径的 `key` 改用中性黄铜钥匙贴图（`/art-themes/rainy-astronomy/objects/key-brass.png`），不再显示保险丝。 |
| 文档运行次数不一致 | 已修。统一为 21 次运行 / 15 失败 / 6 通过，入口指向最终 36 项运行。 |
| 首屏 1.5MB 背景 | 已改。首屏改用 33KB 的 `ui/landing-cover.jpg`；游戏内仍按房间加载 1600×900 背景。 |
| `closeupFor` 未使用 | 已删除。 |
| 面板焦点被移除后 Tab 可能离开 modal | 未修，记录为已知限制。 |

## 6. 复核中发现并修掉的问题（实施过程中）

1. 导航按钮高度 38px（低于 44px）——改为 44px。
2. 生成完成后关卡列表可能延迟一拍——就绪后再补一次刷新。
3. 特写图片在面板里被裁切 / 留白过大——改为绝对定位 `object-fit: contain`，并把特写 PNG 裁剪到 alpha bbox。
4. 结算时场景变成空黑的出口房间——保留上一房间画面作为结算背景。
5. 经典入口卡片拉伸后大面积空墙——卡片随列高拉伸，窗口特写填满。
6. 完成态设备从场景消失——补预载“其他状态”贴图（独立复核发现，见第 5 节）。
7. 手机结算被 stage 裁切——结算层改为可滚动并顶部对齐。
8. 首屏 1.5MB 背景——改为 33KB 压缩封面。

## 5. 未验证 / 已知限制

- **没有真人核验**；`human-reviews/v5-rainy-astronomy-ui/round-01/review.md` 保持未填写。
- **没有真实模型生成的关卡**在这个画面下被检查：本阶段 0 次真实模型/付费调用，合成关卡由 `make_fixture` 加固定改名构成。
- **没有真机/触控设备**；手机结果来自 Playwright 视口与 Chrome。
- 只走到 3 房的第 1、2 间；设备间背景与映射有文件但未在浏览器里实际进入。
- 12 种物件外观没有逐个在浏览器中打开；映射由代码与 manifest 静态核对。
- 没有做加载耗时测量；背景 PNG 约 1.5MB，首次进房间有明显加载。
- 素材是没有图像模型时的手写矢量插画，不是水彩手绘；风格上与旧手绘包不完全一致。
- Tab 焦点循环沿用 `components/panelFocus.ts`，本阶段未新增断言；若焦点控件在面板打开期间被移除，Tab 可能离开 modal（独立复核指出，未修）。
- 线路/顺序面板只验证了结构与渲染，没有在本轮 fixture 里提交一次正确解（顺序与线路答案依赖 fixture 私有数据）。
- 3 房只走到第 2 间；第 3 间（设备间）只有文件与映射证据。
- 未实现雨滴/灯光动效（计划中的 MAY）。

## 6. 单独记录

- 浏览器运行总数 21：15 失败（全部 JSON 保留）、6 通过（仅最终通过保留 PNG，其余 PNG 因体积删除，见 `automated/README.md`）。
- 素材合计约 5.0 MiB，单张背景 ≤ 1.6 MiB，符合计划中的体积建议。
- 提交由 liy222 身份完成；未打 tag、未部署、未启用 Actions。
