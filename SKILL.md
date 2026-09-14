---
name: global-travel-planner
description: 全球范围旅行行程规划、行前复核与临场调整 Skill。输入目的地、日期、天数、人数、预算与偏好，输出可执行、可校验、可继续修改的行程；同时交付对话版 Markdown 攻略与响应式单文件 HTML。使用地图（Google Maps/OpenStreetMap）、官方渠道、餐饮平台和网络攻略等实时信息落线，航班与酒店实时价降级为 Google Flights/Skyscanner/Booking/Agoda 查询链接。Use when the user asks to plan, optimize, review, update, recheck, or publish a worldwide/overseas trip itinerary, including requests based on flight, hotel, attraction, restaurant, route, weather, visa, or safety details.
---

# Global Travel Planner

把旅行需求变成可执行、可校验、可继续修改的全球行程。每次必须同时交付：对话版 Markdown 攻略 + 本地单文件 HTML，两者由同一份已校验 JSON 生成，核心事实一致。只有用户明确要求分享并确认隐私影响后，才额外发布公开链接。

## 工作原则

1. **实时信息不靠记忆。** 开放时间、票价、班次、天气、签证、酒店与航班价必须查询；查不到就标 `unknown` 或标注估算，不伪造来源。
2. **硬事实优先官方。** 开放、预约、票务、签证、交通规则以景点/场馆/机场/政府/运营方官网为准。
3. **航班酒店优先浏览器读价，否则降级为查询链接。** 无免费官方 API。若环境有可用浏览器且能连通目标站，走「浏览器读价」（见 [references/fare-reading.md](references/fare-reading.md)）读取真实价与时刻；否则用 `scripts/build_links.py` 生成 Google Flights/Skyscanner/Booking/Agoda 深链。任何情况都不编造时刻与价格。**读价时 AI 只读不下单、不代过验证码**，登录与人机验证由用户本人完成。
4. **路线必须可行。** POI 要有坐标，主要移动段要有查询所得的方式与时长。
5. **区分事实/体验/估算。** 价格区间必须带来源和查询时间。
6. **保护隐私。** 不把 API Key 写进 JSON/HTML/URL/仓库；公开发布前提示页面会暴露目的地、日期、酒店与路线。
7. **不擅自改环境。** 不自动安装 MCP、扩展或 CLI；缺能力时说明影响并给降级方案。
8. **双输出保持一致。** 缺任一输出、只回摘要或链接、两版不一致，都不算完成。

## 信息源

完整行程默认逐一尝试五类信息源，在 `source_coverage` 为 5 个平台各写一项。详细优先级、status 语义与降级铁律见 [references/data-sources.md](references/data-sources.md)。

| 阶段 | 平台 platform | 平台职责 | 全球工具 |
|---|---|---|---|
| 发现 | `discovery` | 分区、玩法、节奏、避雷 | 网页搜索、博客、Reddit、（面向中国用户可选）小红书 |
| 确认 | `official` | 开放、预约、票务、签证、通知 | 各官网 |
| 落线 | `maps` | 坐标、路线、通勤时长 | Google Maps / OpenStreetMap / Mapbox |
| 餐饮 | `dining` | 餐厅候选池 | Google Places / Yelp / TripAdvisor / OSM |
| 交易 | `booking` | 航班/酒店/门票价格与可订状态 | **降级为查询链接** |

## 能力发现

开始前按「能力」而非客户端名称检查环境：有无地图工具、网页搜索/浏览、文件读写、GitHub 发布能力。

- 有地图工具（含 Google Maps MCP）：查 POI、坐标、路线。
- 无地图工具：仍可给草案，但通勤时长标为待核验，`transport.source` 用 `estimate`，不得谎称已实算。
- 有网页搜索/浏览：查官网、餐饮、攻略。
- **有可用浏览器且目标站可达**：先 snapshot 探活，成功则走浏览器读价拿航班/酒店真实价（用户在环完成登录/验证码）；探活超时或被反爬拦截则立即降级回查询链接，不反复重试。
- 某来源不可用：走合规降级，在 `source_coverage` 记录状态与影响。

## 标准流程

### 1. 归一化需求

收集并确认：目的地、日期、天数、人数、出发地；已订航班/酒店；必去/不去、预算、节奏、饮食禁忌、步行能力；老人/儿童/无障碍/行李/返程缓冲；**签证与护照有效期**（跨境特有）。信息不足先做合理假设并列出，只在会改变检索结果时才追问。

### 2. 五源分阶段研究

先用 discovery 发现分区与风险，用 official 确认硬事实，用 maps 落坐标与路线，用 dining 围绕当日区域找餐厅，最后 booking 处理交易——航班酒店用 `build_links.py` 生成查询链接。为易变事实保存 `source`/`source_ref`/`checked_at`，在 `rechecks` 安排 `recheck_at`。

### 3. 建候选池并排日程

- 每天围绕一个主区域或清晰转场逻辑；
- 先放时间固定、需预约的项目；
- 控制每日 POI 数量与步行强度；
- 餐饮靠近当日区域；
- 末日从返程航班时间倒排，国际航班预留 ≥3 小时（值机+安检+退税+取行李），末日 `region_flex: true`；
- 为天气敏感项写 `plan_b`；按同行人/天气/夜间交通/返程写具体 `safety_notes`。

### 4. 写结构化数据

以 [references/trip-schema.json](references/trip-schema.json) 为准。坐标为全球范围（lng ∈ [-180,180]，lat ∈ [-90,90]）。至少包含：`trip_name`/`destination`/`date_range`/`party_size`；`flights`（降级链接）；`hotel`（坐标+订房链接）；每日 `day`/`date`/`region`/`center`/`pois`（序号/时间/时长/坐标）；`transports`（端点/方式/时长/source）；`prebook`；5 项 `source_coverage`；`plan_b`/`safety_notes`/`rechecks`/`budget_summary`。

生成链接：

```bash
python scripts/build_links.py flight --from PVG --to CDG --depart 2026-10-01 --return 2026-10-03 --adults 2
python scripts/build_links.py hotel --city "Paris" --checkin 2026-10-01 --checkout 2026-10-03 --adults 2
```

详见 [references/link-builders.md](references/link-builders.md)。

**若走浏览器读价**（拿到真实价与时刻后）把结果合并进行程：

```bash
python scripts/record_fares.py --trip trip.json --fares fares.json --in-place
```

它会更新 `flights[].price/note` 并把 `source_coverage.booking` 翻为 `used`。流程与 `fares.json` 结构见 [references/fare-reading.md](references/fare-reading.md)。

### 5. 校验并修正

```bash
python scripts/validate.py trip.json --pretty --fail-on-warn
```

失败或警告先修数据再继续。规则：V0 完整性、V1 区域一致性、V2 时间可行性、V4 一日一重预约、V5 末日返程缓冲、V8 路线来源、V10 价格溯源、V12 复核时效。测试历史/未来日期用 `--as-of YYYY-MM-DD`，真实交付用今天。

### 6. 渲染双输出

```bash
python scripts/render_markdown.py trip.json -o trip.md
python scripts/render_html.py assets/template.html trip.json -o trip.html
```

对话版必须直接使用 `trip.md` 内容。HTML 为单文件、无外部 CDN 依赖，可离线/手机查看。打开检查标题、每日行程、五源覆盖、预约、Plan B、安全提醒、预算与移动端布局。

### 7. 生成对话版攻略

把 `trip.md` 完整内容放进对话（无需打开附件即可用），至少含：概览与关键假设；每日时段/POI 顺序/区域/主要交通；餐饮、预算区间、预约事项与 Plan B；与老人/儿童/天气/返程有关的安全提醒。不要只回「已生成 HTML」或文件链接代替对话版。

### 8. 双交付或额外发布

同一次最终回复中同时给出对话版攻略与 HTML 文件；JSON 是数据源与后续修改底稿，可一并给但不能替代任一可见输出。用户要公开链接时：提示隐私→确认仓库与可见性→发布后实际打开验证→只返回验证过的链接。

## 行前复核与临场调整

按首日日期选核对强度：>7 天保留证据并安排 `recheck_at`；≤7 天重查开放/路线/可售/未付款价格；≤1 天再查逐小时天气、预警、临时闭馆与机场路线；用户说"今天/明天"或现场变化只重算受影响日期。这不是后台定时任务，每次调用按当前日期执行。

## 增量修改

用户改酒店/日期/航班/POI 时不重做无关部分：读现有 JSON → 找受影响项 → 只重查会失效的事实 → 重跑全量校验 → 重新渲染 MD 与 HTML → 用最新 MD 作完整对话版 → 同一回复重新双交付。

## 资源索引

- [references/data-sources.md](references/data-sources.md)：五类信息源、status 语义与降级铁律
- [references/link-builders.md](references/link-builders.md)：航班/酒店/地图查询链接生成
- [references/fare-reading.md](references/fare-reading.md)：浏览器读价模块（用户在环，只读不下单）+ record_fares.py 写回
- [references/trip-schema.json](references/trip-schema.json)：行程 JSON 结构（全球坐标范围）
