# 浏览器读价模块（browser-in-the-loop，用户在环）

用于在**能连通目标站的机器上**（通常是用户自己的电脑）用浏览器读取航班/酒店的真实价格与时刻，替代「降级为查询链接」。核心原则：**AI 只读不下单、不代过验证码、不硬闯**；登录与人机验证由用户本人完成。

## 何时启用（能力门控）

同时满足才启用，否则**降级回查询链接**（见 link-builders.md）：

1. 环境有可用的 `browser` 工具，且目标站点能打开（先用一次 snapshot 探活）；
2. 用户在场，能完成扫码登录与验证码；
3. 用户未要求「只给链接」。

> 远程无公网/无头容器打不开 Google Flights、Skyscanner 等海外站时，直接降级，不要反复重试浏览器。

## 目标站点

| 类型 | 站点 | 是否需登录 |
|---|---|---|
| 航班 | Google Flights / Skyscanner / Kayak / Trip.com | 一般免登录即可看价 |
| 海外酒店 | Booking.com / Agoda / Google Hotels | 免登录可看价，下单才需登录 |
| 国内酒店 | 携程 / 飞猪 | 需扫码登录看会员价/实价 |
| 国内餐饮 | 大众点评 / 美团 | 需扫码登录看评分/人均 |

## 标准流程

1. **探活**：用 `build_links.py` 生成结果页 URL → `browser open` → `browser snapshot`。抓取超时或被反爬拦截 → 立即降级回链接，并在 `source_coverage.booking` 标 `degraded`。
2. **需要登录/验证码时**：把登录页停在浏览器里，**明确请用户本人扫码/滑块/短信验证**，完成后由用户说「好了」再继续。**绝不调用任何自动点选、绕过或模拟验证的手段。**
3. **读价**：页面渲染出结果后 snapshot，提取前 3–5 个**最便宜**选项，每条记录：
   - 价格（含税、币种）、航司、出发/到达时刻、经停数、总时长、（多段则记每段）
   - 抓取时间 `checked_at`、来源站 `source_ref`
4. **多路由比价**：对直飞 / 经 KUL / 经 BKK / 经 SIN 各读一次，横向对比总价与总耗时，给出最划算组合。
5. **写回行程**：把读到的选项用 `record_fares.py` 合并进 `trip.json` 的 `flights[]`，并把 `source_coverage.booking` 翻为 `used`。

## 铁律

- 只读价与时刻，**不下单、不改单、不付款**。
- 验证码/登录**只能用户本人做**；AI 不代做、不硬闯、不用第三方打码。
- 价格是**抓取当时**的值，随库存浮动；交付时标注 `checked_at`，提醒下单前以平台实时价为准。
- 自转机（分段票）风险照旧提示：行李不直挂、误接不赔，留足中转缓冲。

## 写回脚本

```bash
# fares.json 见下方结构；把读到的实价合并进 trip.json
python scripts/record_fares.py --trip trip.json --fares fares.json --in-place
```

`fares.json` 结构：

```json
{
  "checked_at": "2026-09-14",
  "source": "google-flights",
  "source_ref": "https://www.google.com/travel/flights?q=...",
  "flights": [
    {
      "leg": "outbound", "origin": "PVG", "dest": "KUL", "date": "2026-09-26",
      "airlines": "AirAsia X D7", "depart": "12:30", "arrive": "18:10",
      "stops": 0, "duration": "5h40m",
      "price": {"min": 1350, "currency": "CNY", "unit": "人"}
    }
  ]
}
```
