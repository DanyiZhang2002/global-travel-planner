#!/usr/bin/env python3
"""
global-travel-planner 查询链接生成器

用途：航班与酒店没有免费官方 API，采用「降级为查询链接」策略——
根据结构化参数生成 Google Flights / Skyscanner / Booking.com / Google Hotels /
Google Maps 的深链，让用户一键跳转到实时价格页自行核对。

用法：
    python scripts/build_links.py flight  --from HND --to CDG --depart 2026-10-01 [--return 2026-10-08] [--adults 2]
    python scripts/build_links.py hotel   --city "Paris" --checkin 2026-10-01 --checkout 2026-10-08 [--adults 2]
    python scripts/build_links.py map     --name "Louvre Museum" [--lat 48.8606 --lng 2.3376]
    python scripts/build_links.py route   --from "Louvre Museum" --to "Eiffel Tower" [--mode transit]
    python scripts/build_links.py json    --spec spec.json      # 批量：读 {"flights":[...],"hotels":[...]}

所有子命令输出 JSON（stdout），字段含 provider / url。纯标准库，无第三方依赖。
"""
from __future__ import annotations

import argparse
import json
import sys
from urllib.parse import quote, urlencode


def flight_links(origin: str, dest: str, depart: str, ret: str | None = None,
                 adults: int = 1) -> list[dict]:
    """生成主流机票比价站的搜索深链。origin/dest 用 IATA 码或城市名均可。"""
    o, d = origin.strip(), dest.strip()
    links = []
    # Google Flights —— 用查询串形式（稳定、无需登录）
    q = f"flights from {o} to {d} on {depart}"
    if ret:
        q += f" returning {ret}"
    links.append({
        "provider": "Google Flights",
        "url": "https://www.google.com/travel/flights?" + urlencode({"q": q}),
    })
    # Skyscanner —— 路径式深链 yyMMdd
    def _sky(dt: str) -> str:
        return dt.replace("-", "")[2:]
    leg = f"{o.lower()}/{d.lower()}/{_sky(depart)}"
    if ret:
        leg += f"/{_sky(ret)}"
    links.append({
        "provider": "Skyscanner",
        "url": f"https://www.skyscanner.net/transport/flights/{leg}/?adults={adults}",
    })
    # Kayak
    kayak = f"https://www.kayak.com/flights/{o}-{d}/{depart}"
    if ret:
        kayak += f"/{ret}"
    links.append({"provider": "Kayak", "url": kayak + f"?adults={adults}"})
    return links


def hotel_links(city: str, checkin: str, checkout: str, adults: int = 2) -> list[dict]:
    """生成主流酒店比价站的搜索深链。"""
    c = city.strip()
    links = [
        {
            "provider": "Booking.com",
            "url": "https://www.booking.com/searchresults.html?" + urlencode({
                "ss": c, "checkin": checkin, "checkout": checkout, "group_adults": adults,
            }),
        },
        {
            "provider": "Google Hotels",
            "url": "https://www.google.com/travel/hotels/" + quote(c)
                   + "?" + urlencode({"ss": c}),
        },
        {
            "provider": "Agoda",
            "url": "https://www.agoda.com/search?" + urlencode({
                "city": c, "checkIn": checkin, "checkOut": checkout, "adults": adults,
            }),
        },
    ]
    return links


def map_link(name: str, lat: float | None = None, lng: float | None = None) -> list[dict]:
    """POI 地图链接（Google Maps + OSM）。有坐标时用坐标，否则用名称搜索。"""
    if lat is not None and lng is not None:
        g = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
        o = f"https://www.openstreetmap.org/?mlat={lat}&mlon={lng}#map=17/{lat}/{lng}"
    else:
        g = "https://www.google.com/maps/search/?" + urlencode({"api": 1, "query": name})
        o = "https://www.openstreetmap.org/search?" + urlencode({"query": name})
    return [{"provider": "Google Maps", "url": g}, {"provider": "OpenStreetMap", "url": o}]


def route_link(origin: str, dest: str, mode: str = "transit") -> list[dict]:
    """两点路线链接（Google Maps directions）。mode: driving/walking/bicycling/transit"""
    url = "https://www.google.com/maps/dir/?" + urlencode({
        "api": 1, "origin": origin, "destination": dest, "travelmode": mode,
    })
    return [{"provider": "Google Maps Directions", "url": url}]


def main() -> int:
    ap = argparse.ArgumentParser(description="生成航班/酒店/地图查询链接")
    sub = ap.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("flight")
    f.add_argument("--from", dest="origin", required=True)
    f.add_argument("--to", dest="dest", required=True)
    f.add_argument("--depart", required=True)
    f.add_argument("--return", dest="ret", default=None)
    f.add_argument("--adults", type=int, default=1)

    h = sub.add_parser("hotel")
    h.add_argument("--city", required=True)
    h.add_argument("--checkin", required=True)
    h.add_argument("--checkout", required=True)
    h.add_argument("--adults", type=int, default=2)

    m = sub.add_parser("map")
    m.add_argument("--name", required=True)
    m.add_argument("--lat", type=float, default=None)
    m.add_argument("--lng", type=float, default=None)

    r = sub.add_parser("route")
    r.add_argument("--from", dest="origin", required=True)
    r.add_argument("--to", dest="dest", required=True)
    r.add_argument("--mode", default="transit")

    j = sub.add_parser("json")
    j.add_argument("--spec", required=True)

    args = ap.parse_args()

    if args.cmd == "flight":
        out = flight_links(args.origin, args.dest, args.depart, args.ret, args.adults)
    elif args.cmd == "hotel":
        out = hotel_links(args.city, args.checkin, args.checkout, args.adults)
    elif args.cmd == "map":
        out = map_link(args.name, args.lat, args.lng)
    elif args.cmd == "route":
        out = route_link(args.origin, args.dest, args.mode)
    elif args.cmd == "json":
        spec = json.load(open(args.spec, encoding="utf-8"))
        out = {"flights": [], "hotels": []}
        for fl in spec.get("flights", []):
            out["flights"].append({"query": fl, "links": flight_links(**fl)})
        for ho in spec.get("hotels", []):
            out["hotels"].append({"query": ho, "links": hotel_links(**ho)})
    else:
        return 2

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
