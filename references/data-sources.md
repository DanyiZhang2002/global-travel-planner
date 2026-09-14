# 全球信息源与证据规范

完整行程默认逐一尝试五类信息源，按平台属性分阶段使用。`source_coverage` 必须为这 5 个平台各写一项，记录 `status`/`stages`/`purpose`/`checked_at`/`source_refs`。

| 平台 platform | 阶段 stages | 平台职责 | 全球可用工具 |
|---|---|---|---|
| `discovery` | discovery, experience | 发现分区、玩法、节奏、避雷 | 网页搜索、旅游博客、Reddit、（面向中国用户可选）小红书 |
| `official` | constraints, recheck | 开放时间、票务、预约、签证、临时通知 | 景点/博物馆/机场/政府官网 |
| `maps` | spatial, recheck | POI 坐标、路线、通勤时长 | Google Maps（含 MCP）、OpenStreetMap/OSRM、Mapbox |
| `dining` | dining, experience | 餐厅候选池（菜系/预算/位置） | Google Places、Yelp、TripAdvisor、OSM 餐饮 POI |
| `booking` | booking, pricing, recheck | 航班/酒店/门票价格与可订状态 | **降级为查询链接**（Google Flights/Skyscanner/Booking/Agoda/Google Hotels） |

## status 取值

- `used`：实际访问并取到数据，`source_refs` 必须为真实 HTTP(S) 链接
- `degraded`：能力受限，走降级方案（如航班酒店只给查询链接），`source_refs` 填搜索/入口链接，`note` 说明降级原因
- `unavailable`：环境无此能力，`note` 说明影响
- `not_applicable`：该行程确实不需要，`note` 说明原因

## 降级铁律（航班/酒店）

- 航班、酒店实时价**没有免费官方 API**，本 skill 默认策略是「降级为查询链接」，用 `scripts/build_links.py` 生成深链。
- 不得凭记忆或臆测编造航班时刻、票价、酒店房价。价格未查证时 `status` 标 `not_booked`/`unknown`，不写具体数字。
- 若用户提供了付费 API key（Amadeus/Skyscanner 等），才可升级为 `used` 并写实时价，同时记录 `checked_at`。

## 证据规范

- 硬事实（开放/票务/签证/交通规则）以 `official` 为准；`discovery` 只提供软信号，不能覆盖官方。
- 冲突时以最新官方结论为准，并在说明里记录冲突与取舍。
- `source` 字段只证明「声明了来源」，不证明「真的查过」；不要伪造访问痕迹。
