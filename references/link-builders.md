# 查询链接生成器（build_links.py）

航班与酒店没有免费官方 API，用本脚本把结构化参数转成主流平台的搜索深链。纯标准库，无依赖。

## 命令

```bash
# 航班：origin/dest 用 IATA 码或城市名
python scripts/build_links.py flight --from PVG --to CDG --depart 2026-10-01 --return 2026-10-03 --adults 2
# 酒店
python scripts/build_links.py hotel --city "Paris" --checkin 2026-10-01 --checkout 2026-10-03 --adults 2
# 地图（POI）：有坐标优先用坐标
python scripts/build_links.py map --name "Louvre Museum" --lat 48.8606 --lng 2.3376
# 路线（两点方向）：mode = driving|walking|bicycling|transit
python scripts/build_links.py route --from "Louvre Museum" --to "Eiffel Tower" --mode transit
# 批量：读 {"flights":[{...}], "hotels":[{...}]}
python scripts/build_links.py json --spec spec.json
```

## 覆盖的平台

- 航班：Google Flights、Skyscanner、Kayak
- 酒店：Booking.com、Google Hotels、Agoda
- 地图/路线：Google Maps、OpenStreetMap

## 输出如何写进 trip.json

- 航班链接 → `flights[].links`，`flights[].status` 标 `not_booked`/`unknown`
- 酒店链接 → `hotel.booking_links`
- POI 地图链接 → `days[].pois[].map_links`
- 对应把 `source_coverage` 里 `booking` 平台的 `status` 设为 `degraded`，`source_refs` 填这些链接

## 注意

- 深链格式随平台改版可能失效；生成后建议实际打开一条抽查。
- 访问海外站点走内网代理，能否连通需实测；连不通时仍可把链接交付给用户在本地浏览器打开。
