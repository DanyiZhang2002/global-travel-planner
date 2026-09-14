#!/usr/bin/env python3
"""
把浏览器读到的真实票价/时刻（fares.json）合并回 trip.json 的 flights[]，
并把 source_coverage.booking 从 degraded 翻为 used（附 checked_at + source_ref）。

用法：
    python scripts/record_fares.py --trip trip.json --fares fares.json --in-place
    python scripts/record_fares.py --trip trip.json --fares fares.json -o trip.filled.json

fares.json 结构见 references/fare-reading.md。合并规则：
    - 按 (leg, origin, dest, date) 匹配已有 flights[]；命中则更新 price/note，未命中则追加
    - note 自动拼接 航司/时刻/经停/时长，便于对话版与 HTML 展示
    - 只写价格与时刻，status 保持不变（读价 ≠ 已预订）
纯标准库，无第三方依赖。
"""
from __future__ import annotations
import argparse, json, sys


def _key(f: dict) -> tuple:
    return (f.get("leg"), f.get("origin"), f.get("dest"), f.get("date"))


def _note(f: dict) -> str:
    parts = []
    if f.get("airlines"):
        parts.append(str(f["airlines"]))
    if f.get("depart") or f.get("arrive"):
        parts.append(f"{f.get('depart','?')}→{f.get('arrive','?')}")
    if f.get("stops") is not None:
        parts.append("直飞" if f.get("stops") == 0 else f"{f['stops']}次经停")
    if f.get("duration"):
        parts.append(str(f["duration"]))
    return " · ".join(parts)


def merge(trip: dict, fares: dict) -> dict:
    checked_at = fares.get("checked_at")
    source = fares.get("source", "browser-read")
    source_ref = fares.get("source_ref")

    trip.setdefault("flights", [])
    existing = {_key(f): f for f in trip["flights"]}

    for fr in fares.get("flights", []):
        price = dict(fr.get("price") or {})
        if price:
            price.setdefault("source", source)
            if source_ref:
                price.setdefault("source_ref", source_ref)
            if checked_at:
                price.setdefault("checked_at", checked_at)
        note = _note(fr)
        k = _key(fr)
        if k in existing:
            tgt = existing[k]
            if price:
                tgt["price"] = price
            if note:
                tgt["note"] = note
        else:
            entry = {
                "leg": fr.get("leg", "outbound"),
                "origin": fr.get("origin"), "dest": fr.get("dest"), "date": fr.get("date"),
                "status": fr.get("status", "not_booked"),
                "links": fr.get("links", []),
            }
            if price:
                entry["price"] = price
            if note:
                entry["note"] = note
            trip["flights"].append(entry)

    # 翻转 booking 覆盖状态为 used
    for c in trip.get("source_coverage", []):
        if c.get("platform") == "booking":
            c["status"] = "used"
            if checked_at:
                c["checked_at"] = checked_at
            refs = c.get("source_refs") or []
            if source_ref and source_ref not in refs:
                refs.append(source_ref)
            c["source_refs"] = refs
            c["note"] = f"浏览器读价（{source}），实价随库存浮动，下单前以平台实时价为准"
            if "pricing" not in (c.get("stages") or []):
                c.setdefault("stages", []).append("pricing")
    return trip


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trip", required=True)
    ap.add_argument("--fares", required=True)
    ap.add_argument("--in-place", action="store_true")
    ap.add_argument("-o", "--output", default=None)
    a = ap.parse_args()

    trip = json.load(open(a.trip, encoding="utf-8"))
    fares = json.load(open(a.fares, encoding="utf-8"))
    merged = merge(trip, fares)

    out = a.trip if a.in_place else a.output
    if out:
        json.dump(merged, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"wrote {out}; flights={len(merged.get('flights', []))}")
    else:
        print(json.dumps(merged, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
