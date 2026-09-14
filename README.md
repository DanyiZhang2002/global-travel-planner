# global-travel-planner

全球范围旅行行程规划 AI Agent Skill（Codex / Claude Code / Cursor 通用）。

输入目的地、日期、天数、人数、预算与偏好，输出**可执行、可校验、可继续修改**的行程，并同时交付：

- **对话版 Markdown 攻略**：完整日程、交通、餐饮、预算、预约、Plan B、安全提醒直接显示在聊天中；
- **单文件 HTML**：响应式、可离线、可分享给同行人，无外部 CDN 依赖。

## 特点

- 🌍 **全球范围**：坐标放开到全球（不限国内），地图/POI 走 Google Maps / OpenStreetMap。
- 🔎 **信息可溯源**：五类信息源（发现 / 官方 / 地图 / 餐饮 / 交易）各记录状态与核对时间，冲突以官方为准。
- ✈️ **航班酒店两种取价模式**：
  - **浏览器读价**（默认优先）：在能连通比价站的机器上打开 Google Flights / Skyscanner / Booking，用户在环完成登录/验证码，AI 只读价不下单；
  - **降级为查询链接**：环境打不开目标站时，自动生成比价深链，绝不编造价格。
- ✅ **硬校验**：`validate.py` 覆盖区域一致性、时间可行性、返程缓冲、价格溯源、复核时效等规则。
- 🔁 **行前复核与增量修改**：换酒店/航班/景点后只重算受影响部分。

## 安装

把本仓库克隆到 AI 客户端的 skills 目录，例如：

```bash
git clone https://github.com/<yourname>/global-travel-planner.git ~/.codex/skills/global-travel-planner
```

重启客户端后，直接说需求即可，例如：

> 帮我规划马尔代夫 5 天以上，9/25 之后走、10/7 之前回，比较直飞 vs 经吉隆坡/曼谷/新加坡中转哪个机票最划算，中转城市顺便玩 3 天。

## 本地验证与渲染

只需 Python 3.10+，无第三方依赖：

```bash
python scripts/validate.py examples/maldives-5d.json --pretty --as-of 2026-09-14
python scripts/render_markdown.py examples/maldives-5d.json -o /tmp/trip.md
python scripts/render_html.py assets/template.html examples/maldives-5d.json -o /tmp/trip.html
```

## 目录结构

```
SKILL.md                    # 主流程与原则
scripts/
  build_links.py            # 航班/酒店/地图查询链接生成
  record_fares.py           # 把浏览器读到的实价写回行程 JSON
  validate.py               # 行程校验
  render_markdown.py        # 对话版攻略
  render_html.py            # 单文件 HTML
references/
  trip-schema.json          # 行程数据结构（全球坐标）
  data-sources.md           # 五类信息源与降级铁律
  link-builders.md          # 查询链接说明
  fare-reading.md           # 浏览器读价模块（用户在环）
assets/template.html        # HTML 模板
examples/                   # 巴黎 3 天 / 马尔代夫 5 天 示例
```

## 说明

- 所有价格/开放/班次信息为查询当时的值，随季节与库存浮动，预订前以平台实时价为准。
- 本 Skill 只读取价格与信息，**不代为下单、改单或付款**；登录与人机验证由用户本人完成。

## License

[MIT](LICENSE)
