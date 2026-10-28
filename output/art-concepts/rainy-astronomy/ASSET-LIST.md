# 素材清单 · rainy-astronomy

主题包 `rainy-astronomy` / `1.0.0`，显示名「雨夜天文社」。
本文件由 `source/asset_report.py` 按实际构建结果生成：尺寸、bbox、文件大小都来自磁盘上的 PNG。

## 已接入背景（3）

| 背景ID | 用途 | 文件 | 尺寸 | 大小 |
|---|---|---|---|---|
| `neutral_lab` | 天文社旧活动室（1/2/3房第一间） | `/art-themes/rainy-astronomy/backgrounds/neutral_lab.png` | 1600×900 | 1546 KB |
| `neutral_archive` | 封存观测资料空间 | `/art-themes/rainy-astronomy/backgrounds/neutral_archive.png` | 1600×900 | 1542 KB |
| `neutral_control` | 观测设备空间 | `/art-themes/rainy-astronomy/backgrounds/neutral_control.png` | 1600×900 | 92 KB |

## 已接入物件与特写

| 角色 | 变体 | 状态 | 场景图 | 特写 | bbox | 场景/特写大小 |
|---|---|---|---|---|---|---|
| 资料纸面 | `note-logbook` | 默认 | `/art-themes/rainy-astronomy/objects/note-logbook.png` | `/art-themes/rainy-astronomy/closeups/note-logbook.png` | 586×336 | 41 KB / 85 KB |
| 资料纸面 | `note-chart` | 默认 | `/art-themes/rainy-astronomy/objects/note-chart.png` | `/art-themes/rainy-astronomy/closeups/note-chart.png` | 497×433 | 115 KB / 251 KB |
| 资料纸面 | `note-sealed` | 默认 | `/art-themes/rainy-astronomy/objects/note-sealed.png` | `/art-themes/rainy-astronomy/closeups/note-sealed.png` | 470×349 | 44 KB / 86 KB |
| 钥匙 | `key-brass` | 默认 | `/art-themes/rainy-astronomy/objects/key-brass.png` | `/art-themes/rainy-astronomy/closeups/key-brass.png` | 424×367 | 45 KB / 97 KB |
| 资料终端 | `terminal-off` | 默认 | `/art-themes/rainy-astronomy/objects/terminal-off.png` | `/art-themes/rainy-astronomy/closeups/terminal-off.png` | 408×434 | 57 KB / 110 KB |
| 资料终端 | `terminal-on` | 完成 | `/art-themes/rainy-astronomy/objects/terminal-on.png` | `/art-themes/rainy-astronomy/closeups/terminal-on.png` | 409×434 | 63 KB / 131 KB |
| 资料柜 | `cabinet-closed` | 默认 | `/art-themes/rainy-astronomy/objects/cabinet-closed.png` | `/art-themes/rainy-astronomy/closeups/cabinet-closed.png` | 392×454 | 49 KB / 93 KB |
| 资料柜 | `cabinet-open` | 完成 | `/art-themes/rainy-astronomy/objects/cabinet-open.png` | `/art-themes/rainy-astronomy/closeups/cabinet-open.png` | 457×454 | 59 KB / 118 KB |
| 配电设备 | `circuit-off` | 默认 | `/art-themes/rainy-astronomy/objects/circuit-off.png` | `/art-themes/rainy-astronomy/closeups/circuit-off.png` | 443×426 | 35 KB / 70 KB |
| 配电设备 | `circuit-on` | 完成 | `/art-themes/rainy-astronomy/objects/circuit-on.png` | `/art-themes/rainy-astronomy/closeups/circuit-on.png` | 443×426 | 38 KB / 74 KB |
| 顺序面板 | `panel-idle` | 默认 | `/art-themes/rainy-astronomy/objects/panel-idle.png` | `/art-themes/rainy-astronomy/closeups/panel-idle.png` | 368×445 | 47 KB / 94 KB |
| 顺序面板 | `panel-lit` | 完成 | `/art-themes/rainy-astronomy/objects/panel-lit.png` | `/art-themes/rainy-astronomy/closeups/panel-lit.png` | 368×445 | 52 KB / 102 KB |

物件与特写合计约 1.9 MiB。

## 覆盖与未覆盖

- 三个原背景角色 `neutral_lab / neutral_archive / neutral_control` 都有专属画面；服务端背景ID不变。
- 六个物件角色 note / key / terminal / cabinet / circuit / panel 全部有专属外观；资料纸面另有观测记录册、星图资料页、封存便笺三种外观，按公开物件名称选择。
- terminal / cabinet / circuit / panel 各有默认与「已完成」两种状态图；状态来自服务端公开 `completed`，前端不推导中间步骤。
- 每个外观都有独立特写文件（`/art-themes/rainy-astronomy/closeups/`），场景、物品与特写使用同一张矢量源绘制。
- 未覆盖：其他主题（图书馆、化学实验室等）没有专属美术，按设计回退到原有通用手绘素材；包内也没有新的可交互望远镜、星象仪等玩法物件。
- 图中不含真实密码、线路方向、设备顺序或线索数值；这些仍由服务端数据在界面中绘制。

## 资源来源

全部图像由本目录 `source/` 下的 SVG 源文件经本机 headless Chrome 渲染得到，未使用图像生成模型或外部付费服务。
渲染命令见 `source/build.py`；提示词文档见 `prompts/`（记录的是本阶段实际使用的矢量绘制说明，不是模型提示词）。
