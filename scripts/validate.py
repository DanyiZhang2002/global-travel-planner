#!/usr/bin/env python3
"""
global-travel-planner 校验脚本（全球版）

用法：
    python scripts/validate.py trip.json [--pretty] [--fail-on-warn] [--as-of YYYY-MM-DD]

规则：
    V0  核心数据完整性（schema + 五类信息源 + POI 坐标 + transport 端点）
    V1  区域一致性（POI 到当日主区域中心的直线距离）—— 末日/region_flex 跳过
    V2  时间可行性粗算（通勤占比 + 单段最长）
    V4  一日一重预约（当日 prebook 条数）
    V5  末日返程缓冲（国际航班默认 3h）
    V8  路线来源声明（transport.source 必须为允许值 + duration_min>0）
    V10 价格溯源（price.source 不能为臆测来源）
    V12 复核时效（recheck 状态 due/unknown 拦截；checked_at 过期告警）

坐标为全球范围：lng ∈ [-180,180]，lat ∈ [-90,90]。
source 字段只能验证声明是否完整，不能证明外部查询真的发生过。
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import date, datetime
from typing import Any
from urllib.parse import urlparse

# ---- 阈值 ----
V1_WARN_KM, V1_FAIL_KM = 4.0, 8.0          # 全球城市尺度略放宽
V2_COMMUTE_RATIO_WARN, V2_COMMUTE_RATIO_FAIL = 0.35, 0.50
V4_FAIL_PER_DAY = 2
V5_BUFFER_HOURS_FAIL, V5_BUFFER_HOURS_WARN = 3.0, 3.5   # 国际航班
WALK_KMH, TRANSIT_KMH, BIKE_KMH, DRIVE_KMH = 5.0, 25.0, 12.0, 40.0
V8_ALLOWED_SOURCES = {"google-maps", "osm-osrm", "web-search", "estimate"}
V10_BAD_SOURCES = {"", "ai-guess", "memory", "estimate", "demo-estimate", "guess"}
PLATFORM_STAGES = {
    "discovery": {"discovery", "experience"},
    "official":  {"constraints", "recheck"},
    "maps":      {"spatial", "recheck"},
    "dining":    {"dining", "experience"},
    "booking":   {"booking", "pricing", "recheck"},
}
STATUSES = {"used", "degraded", "unavailable", "not_applicable"}
ALL_STAGES = set().union(*PLATFORM_STAGES.values())
EARTH_R_KM = 6371.0088


def get_loc(p: Any) -> tuple[float, float] | None:
    if not isinstance(p, dict):
        return None
    loc = p.get("location")
    if isinstance(loc, (list, tuple)) and len(loc) >= 2:
        return (float(loc[0]), float(loc[1]))
    if "lng" in p and "lat" in p:
        return (float(p["lng"]), float(p["lat"]))
    return None


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lng1, lat1 = a
    lng2, lat2 = b
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    h = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_R_KM * math.asin(math.sqrt(h))


def commute_minutes(a, b, mode="transit") -> float:
    d = haversine_km(a, b)
    m = (mode or "").lower()
    if m in ("walk", "walking"):
        return d / WALK_KMH * 60
    if m in ("bike", "cycling", "biking"):
        return d / BIKE_KMH * 60
    if m in ("drive", "driving", "taxi", "car"):
        return d / DRIVE_KMH * 60
    return d / TRANSIT_KMH * 60


def st(v, warn, fail) -> str:
    return "❌" if v >= fail else ("⚠️" if v >= warn else "✅")


def as_date(v) -> date | None:
    raw = str(v or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except ValueError:
            return None


def is_url(v) -> bool:
    try:
        p = urlparse(str(v or "").strip())
    except ValueError:
        return False
    return p.scheme in {"http", "https"} and bool(p.netloc)


def check_v0(trip) -> dict:
    e: list[str] = []
    for f in ("trip_name", "destination", "date_range"):
        if not str(trip.get(f) or "").strip():
            e.append(f"缺 {f}")
    if not isinstance(trip.get("party_size"), int) or trip.get("party_size", 0) < 1:
        e.append("party_size 必须为正整数")

    sc = trip.get("source_coverage")
    seen = set()
    if not isinstance(sc, list):
        e.append("source_coverage 必须为数组")
    else:
        for i, it in enumerate(sc):
            lb = f"source_coverage[{i}]"
            if not isinstance(it, dict):
                e.append(f"{lb} 必须为对象"); continue
            pf = it.get("platform")
            if pf not in PLATFORM_STAGES:
                e.append(f"{lb}.platform 不合法"); continue
            if pf in seen:
                e.append(f"{lb}.platform 重复：{pf}")
            seen.add(pf)
            if it.get("status") not in STATUSES:
                e.append(f"{lb}.status 不合法")
            stages = it.get("stages")
            if not isinstance(stages, list) or not stages:
                e.append(f"{lb}.stages 必须为非空数组")
            else:
                if [s for s in stages if s not in ALL_STAGES]:
                    e.append(f"{lb}.stages 含无效阶段")
                if not set(stages) & PLATFORM_STAGES[pf]:
                    e.append(f"{lb}.stages 不符合 {pf} 平台职责")
            for f in ("purpose", "checked_at"):
                if not str(it.get(f) or "").strip():
                    e.append(f"{lb}.{f} 不能为空")
            refs = it.get("source_refs")
            if not isinstance(refs, list):
                e.append(f"{lb}.source_refs 必须为数组")
            elif it.get("status") in {"used", "degraded"}:
                if not refs:
                    e.append(f"{lb}.source_refs 使用/降级时不能为空")
                elif any(not is_url(r) for r in refs):
                    e.append(f"{lb}.source_refs 只能是 HTTP(S) 链接")
            if it.get("status") in {"unavailable", "not_applicable"} and not str(it.get("note") or "").strip():
                e.append(f"{lb}.note 必须说明原因")
        miss = set(PLATFORM_STAGES) - seen
        if miss:
            e.append(f"source_coverage 缺平台：{sorted(miss)}")

    days = trip.get("days")
    if not isinstance(days, list) or not days:
        e.append("days 必须为非空数组"); days = []
    for di, day in enumerate(days):
        lb = f"days[{di}]"
        if not isinstance(day, dict):
            e.append(f"{lb} 必须为对象"); continue
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(day.get("date") or "")):
            e.append(f"{lb}.date 必须为 YYYY-MM-DD")
        if not str(day.get("region") or "").strip():
            e.append(f"{lb}.region 不能为空")
        if get_loc({"location": day.get("center")}) is None:
            e.append(f"{lb}.center 缺有效经纬度")
        pois = day.get("pois")
        if not isinstance(pois, list) or not pois:
            e.append(f"{lb}.pois 必须为非空数组"); continue
        idxs = []
        for pi, poi in enumerate(pois):
            pl = f"{lb}.pois[{pi}]"
            if not isinstance(poi, dict):
                e.append(f"{pl} 必须为对象"); continue
            idx = poi.get("idx")
            if not isinstance(idx, int) or idx < 1:
                e.append(f"{pl}.idx 必须为正整数")
            else:
                idxs.append(idx)
            if not str(poi.get("name") or "").strip():
                e.append(f"{pl}.name 不能为空")
            if not re.match(r"^\d{1,2}:\d{2}", str(poi.get("time") or "")):
                e.append(f"{pl}.time 缺有效时间")
            if not isinstance(poi.get("duration_min"), (int, float)) or poi.get("duration_min", 0) <= 0:
                e.append(f"{pl}.duration_min 必须大于 0")
            if get_loc(poi) is None:
                e.append(f"{pl} 缺有效经纬度")
        if len(idxs) != len(set(idxs)):
            e.append(f"{lb}.pois 存在重复 idx")
        ep = {0, *idxs}
        for ti, t in enumerate(day.get("transports") or []):
            tl = f"{lb}.transports[{ti}]"
            if not isinstance(t, dict):
                e.append(f"{tl} 必须为对象"); continue
            if t.get("from_idx") not in ep:
                e.append(f"{tl}.from_idx 不对应酒店(0)或当日 POI")
            if t.get("to_idx") not in ep:
                e.append(f"{tl}.to_idx 不对应酒店(0)或当日 POI")

    sn = trip.get("safety_notes")
    if not isinstance(sn, list) or not sn:
        e.append("safety_notes 必须为非空数组")

    if e:
        return {"id": "V0", "rule": "核心数据完整性", "status": "❌",
                "note": f"{len(e)} 项错误：{e[:6]}{'...' if len(e) > 6 else ''}", "errors": e}
    return {"id": "V0", "rule": "核心数据完整性", "status": "✅", "note": "核心字段/五源覆盖/坐标/端点完整"}


def check_v1(day, is_last) -> dict:
    center, pois = day.get("center"), day.get("pois") or []
    region = day.get("region", "?")
    if not center or not pois:
        return {"id": "V1", "rule": "区域一致性", "status": "⚠️", "note": "缺 center/pois"}
    if is_last:
        return {"id": "V1", "rule": "区域一致性", "status": "✅", "note": f"末日（{region}）跳过距离检查（用 V5 验缓冲）"}
    if day.get("region_flex") is True:
        return {"id": "V1", "rule": "区域一致性", "status": "✅", "note": f"跨区日（{region}）region_flex 跳过"}
    worst, wname = 0.0, None
    for p in pois:
        loc = get_loc(p)
        if loc is None:
            continue
        d = haversine_km(tuple(center), loc)
        if d > worst:
            worst, wname = d, p.get("name", "?")
    return {"id": "V1", "rule": "区域一致性", "status": st(worst, V1_WARN_KM, V1_FAIL_KM),
            "note": f"主区域 {region}，最远 POI「{wname}」{worst:.2f} km（阈值 {V1_WARN_KM}/{V1_FAIL_KM}）"}


def check_v2(day) -> dict:
    pois = day.get("pois") or []
    if len(pois) < 2:
        return {"id": "V2", "rule": "时间可行性粗算", "status": "✅", "note": "单 POI 日跳过"}
    tc = ts = worst = 0.0
    wpair = None
    for i in range(len(pois) - 1):
        a, b = get_loc(pois[i]), get_loc(pois[i + 1])
        if not a or not b:
            continue
        cm = commute_minutes(a, b, pois[i].get("next_mode", "transit"))
        tc += cm
        if cm > worst:
            worst, wpair = cm, (pois[i].get("name", "?"), pois[i + 1].get("name", "?"))
    for p in pois:
        ts += p.get("duration_min", 0)
    if ts == 0:
        return {"id": "V2", "rule": "时间可行性粗算", "status": "⚠️", "note": "缺 duration_min"}
    ratio = tc / (tc + ts)
    pair = f"{wpair[0]}→{wpair[1]}" if wpair else "?"
    return {"id": "V2", "rule": "时间可行性粗算", "status": st(ratio, V2_COMMUTE_RATIO_WARN, V2_COMMUTE_RATIO_FAIL),
            "note": f"通勤占比 {ratio*100:.1f}%，最长段 {worst:.0f}min（{pair}，粗算，建议用地图复核）"}


def check_v4(day, prebook) -> dict:
    di = day.get("day")
    cnt = 0
    for p in prebook:
        note = p.get("note") or ""
        if p.get("day") == di or (f"Day {di}" in note and "出发前" not in note):
            cnt += 1
    return {"id": "V4", "rule": "一日一重预约", "status": "❌" if cnt >= V4_FAIL_PER_DAY else "✅",
            "note": f"Day {di} 当日需预约 {cnt} 项"}


def check_v5(trip) -> dict:
    """末日返程缓冲：从末日最后一个 POI 到出发（航班）预留时间。启发式，用 note/flights 提示。"""
    flights = trip.get("flights") or []
    ret = [f for f in flights if f.get("leg") in ("return", "outbound")]
    if not ret:
        return {"id": "V5", "rule": "末日返程缓冲", "status": "⚠️", "note": "无 flights 信息，无法验缓冲（人工确认）"}
    return {"id": "V5", "rule": "末日返程缓冲", "status": "✅",
            "note": f"国际航班建议末日预留 ≥{V5_BUFFER_HOURS_FAIL}h（安检+值机+取行李），请人工确认末班 POI 结束时间"}


def check_v8(days) -> dict:
    bad = []
    for day in days:
        for t in day.get("transports") or []:
            src = t.get("source")
            if src not in V8_ALLOWED_SOURCES:
                bad.append(f"Day{day.get('day')} source={src!r}")
            if not isinstance(t.get("duration_min"), (int, float)) or t.get("duration_min", 0) <= 0:
                bad.append(f"Day{day.get('day')} duration_min 缺失")
    if bad:
        return {"id": "V8", "rule": "路线来源声明", "status": "❌", "note": f"{bad[:5]}"}
    return {"id": "V8", "rule": "路线来源声明", "status": "✅", "note": "transport 来源与时长声明完整"}


def _walk_prices(obj, hits):
    if isinstance(obj, dict):
        if "source" in obj and ("min" in obj or "max" in obj or "total_min" in obj):
            if str(obj.get("source") or "").strip().lower() in V10_BAD_SOURCES:
                hits.append(obj.get("source"))
        for v in obj.values():
            _walk_prices(v, hits)
    elif isinstance(obj, list):
        for v in obj:
            _walk_prices(v, hits)


def check_v10(trip) -> dict:
    hits: list = []
    _walk_prices(trip, hits)
    if hits:
        return {"id": "V10", "rule": "价格溯源", "status": "⚠️", "note": f"发现臆测价格来源：{hits[:5]}（应改为查询链接或标 unknown）"}
    return {"id": "V10", "rule": "价格溯源", "status": "✅", "note": "无臆测价格来源"}


def check_v12(trip, as_of) -> dict:
    rc = trip.get("rechecks") or []
    due = [r.get("item") for r in rc if r.get("status") in ("due", "unknown")]
    stale = []
    for r in rc:
        ra = as_date(r.get("recheck_at"))
        if ra and ra < as_of and r.get("status") == "verified":
            stale.append(r.get("item"))
    if due:
        return {"id": "V12", "rule": "复核时效", "status": "❌", "note": f"待复核/未知：{due[:5]}"}
    if stale:
        return {"id": "V12", "rule": "复核时效", "status": "⚠️", "note": f"已过 recheck_at 需重查：{stale[:5]}"}
    return {"id": "V12", "rule": "复核时效", "status": "✅", "note": "复核项均在有效期内"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("trip")
    ap.add_argument("--pretty", action="store_true")
    ap.add_argument("--fail-on-warn", action="store_true")
    ap.add_argument("--as-of", default=None)
    a = ap.parse_args()

    as_of = as_date(a.as_of) or date.today()
    trip = json.load(open(a.trip, encoding="utf-8"))
    days = trip.get("days") or []
    prebook = trip.get("prebook") or []

    report = [check_v0(trip)]
    for i, day in enumerate(days):
        report.append({**check_v1(day, i == len(days) - 1), "day": day.get("day")})
        report.append({**check_v2(day), "day": day.get("day")})
        report.append({**check_v4(day, prebook), "day": day.get("day")})
    report.append(check_v5(trip))
    report.append(check_v8(days))
    report.append(check_v10(trip))
    report.append(check_v12(trip, as_of))

    fails = [r for r in report if r["status"] == "❌"]
    warns = [r for r in report if r["status"] == "⚠️"]
    ok = not fails and (not warns or not a.fail_on_warn)
    out = {"as_of": as_of.isoformat(), "passed": ok,
           "summary": {"fail": len(fails), "warn": len(warns), "pass": len(report) - len(fails) - len(warns)},
           "report": report}
    print(json.dumps(out, ensure_ascii=False, indent=2 if a.pretty else None))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
