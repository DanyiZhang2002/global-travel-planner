# global-travel-planner

**找到最便宜的出行方式**为核心的全球旅行 AI Agent Skill（Codex / Claude Code / Cursor 通用）。

给它一个出行窗口和目的地，它会把「直飞 + 各中转枢纽 × 多个候选日期」的往返组合全部列出、读取真实票价、**按总价从低到高排名**，直接告诉你「哪个组合、哪几天、一共多少钱」。也能顺带生成完整行程攻略。

## 两种模式

### 🎯 fare-scan：找最便宜怎么飞（核心）

诉求是「找最划算机票」时用它，不排冗长行程：

```bash
# 1) 生成扫描计划：枚举组合 + 每段比价链接（可离线）
python scripts/fare_scan.py plan --from PVG --to MLE \
    --window-start 2026-09-25 --window-end 2026-10-07 \
    --min-stay 5 --hubs KUL,BKK,SIN --hub-stay 3 --adults 2 --direct -o plan.json

# 2) 本地用浏览器读到实价、填入每段 price.min 后，按总价排名
python scripts/fare_scan.py rank --results plan.filled.json
```

输出示例：

```
🥇 PVG→KUL→MLE（中转吉隆坡，玩3天）  单人 ¥2800 ×2 = ¥5600
   PVG→KUL 09-27 ¥1100 + KUL→MLE 09-30 ¥1400 + MLE→PVG 10-05 ¥1900
🥈 ...
```

**省钱逻辑**：拆票（分段购买）通常比联程便宜；出发段与转飞段的谷底价常不在同一天，用候选日期矩阵去凑；中转停留天然规避误接风险。

### 🗺️ 完整行程规划（附带）

要一份可执行行程单时，输出**对话版 Markdown 攻略 + 单文件 HTML**（响应式、可离线、可分享），含日程、交通、餐饮、预算、预约、Plan B、安全提醒，信息可溯源。

## 票价怎么来的（真实、不编造）

- **浏览器读价**（默认优先）：在能连通比价站的机器上打开 Google Flights / Skyscanner / Booking，**用户在环完成登录/验证码，AI 只读价不下单**。
- **降级为查询链接**：环境打不开目标站时，自动生成比价深链，绝不编造价格。

## 安装

```bash
git clone https://github.com/DanyiZhang2002/global-travel-planner.git ~/.codex/skills/global-travel-planner
# 重启客户端即可识别；Claude Code 用 ~/.claude/skills/，Cursor 用对应 skills 目录
```

本地跑真实价的前提：机器上有 Chrome、客户端开启了浏览器工具、目标比价站可访问。

## 本地验证与渲染

只需 Python 3.10+，无第三方依赖：

```bash
python scripts/fare_scan.py plan --from PVG --to MLE --window-start 2026-09-25 --window-end 2026-10-07 --min-stay 5 --adults 2 --direct
python scripts/validate.py examples/maldives-5d.json --pretty --as-of 2026-09-14
python scripts/render_markdown.py examples/maldives-5d.json -o /tmp/trip.md
python scripts/render_html.py assets/template.html examples/maldives-5d.json -o /tmp/trip.html
```

## 目录结构

```
SKILL.md                    # 主流程：先判断 fare-scan 还是完整行程
scripts/
  fare_scan.py              # ★ 找最便宜：多路由×多日期扫描 + 按总价排名
  build_links.py            # 航班/酒店/地图查询链接生成
  record_fares.py           # 把浏览器读到的实价写回行程 JSON
  validate.py               # 行程校验
  render_markdown.py        # 对话版攻略
  render_html.py            # 单文件 HTML
references/
  fare-scan.md              # ★ fare-scan 模式用法与省钱铁律
  fare-reading.md           # 浏览器读价模块（用户在环，只读不下单）
  link-builders.md          # 查询链接说明
  data-sources.md           # 五类信息源与降级铁律
  trip-schema.json          # 行程数据结构（全球坐标）
assets/template.html        # HTML 模板
examples/                   # 巴黎 3 天 / 马尔代夫 5 天 示例
```

## 说明

- 所有价格/开放/班次为查询当时的值，随季节与库存浮动，预订前以平台实时价为准。
- 本 Skill 只读取价格与信息，**不代为下单、改单或付款**；登录与人机验证由用户本人完成。

## License

[MIT](LICENSE)
