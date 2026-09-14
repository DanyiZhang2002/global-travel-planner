#!/usr/bin/env python3
"""
把 trip.json 渲染为对话版 Markdown 攻略。
用法：python scripts/render_markdown.py trip.json -o trip.md
"""
from __future__ import annotations
import argparse, json, sys


def price_str(p: dict | None) -> str:
    if not isinstance(p, dict):
        return ""
    cur = p.get("currency", "USD")
    if "total_min" in p or "total_max" in p:
        lo, hi = p.get("total_min"), p.get("total_max")
    else:
        lo, hi = p.get("min"), p.get("max")
    if lo is None and hi is None:
        return ""
    if lo is not None and hi is not None and lo != hi:
        body = f"{cur} {lo:g}–{hi:g}"
    else:
        body = f"{cur} {(lo if lo is not None else hi):g}"
    if p.get("unit"):
        body += f"/{p['unit']}"
    return body


def links_str(links) -> str:
    if not links:
        return ""
    return " · ".join(f"[{l['provider']}]({l['url']})" for l in links if l.get("url"))


def render(trip: dict) -> str:
    L: list[str] = []
    L.append(f"# {trip.get('trip_name','行程')}\n")
    meta = [f"**目的地**：{trip.get('destination','')}"]
    if trip.get("country"):
        meta.append(f"**国家/地区**：{trip['country']}")
    meta.append(f"**日期**：{trip.get('date_range','')}")
    meta.append(f"**人数**：{trip.get('party_size','')}")
    if trip.get("origin"):
        meta.append(f"**出发地**：{trip['origin']}")
    L.append(" ｜ ".join(meta) + "\n")
    if trip.get("summary"):
        L.append(f"> {trip['summary']}\n")

    if trip.get("assumptions"):
        L.append("## 关键假设与待核验")
        for a in trip["assumptions"]:
            L.append(f"- {a}")
        L.append("")

    # 航班（降级为查询链接）
    if trip.get("flights"):
        L.append("## ✈️ 航班（查询链接，实时价请点开核对）")
        for f in trip["flights"]:
            leg = {"outbound": "去程", "return": "返程", "internal": "内陆"}.get(f.get("leg"), f.get("leg"))
            line = f"- **{leg}** {f.get('origin')} → {f.get('dest')}　{f.get('date','')}　状态：{f.get('status','unknown')}"
            L.append(line)
            if f.get("links"):
                L.append(f"  - 比价：{links_str(f['links'])}")
            if f.get("note"):
                L.append(f"  - {f['note']}")
        L.append("")

    # 酒店
    if trip.get("hotel"):
        h = trip["hotel"]
        L.append("## 🏨 酒店")
        L.append(f"- **{h.get('name','')}**　{h.get('address','')}")
        if h.get("why"):
            L.append(f"  - 选择理由：{h['why']}")
        if h.get("price"):
            ps = price_str(h["price"])
            if ps:
                L.append(f"  - 参考价：{ps}")
        if h.get("booking_links"):
            L.append(f"  - 订房：{links_str(h['booking_links'])}")
        L.append("")

    # 每日行程
    for day in trip.get("days", []):
        head = f"## Day {day.get('day')}　{day.get('date','')}　{day.get('region','')}"
        if day.get("theme"):
            head += f"　—　{day['theme']}"
        L.append(head)
        if day.get("weather"):
            L.append(f"*天气*：{day['weather']}")
        for p in day.get("pois", []):
            row = f"- `{p.get('time','')}` **{p.get('name','')}**（约 {p.get('duration_min',0):g} 分钟）"
            L.append(row)
            extra = []
            if p.get("price"):
                ps = price_str(p["price"])
                if ps:
                    extra.append(f"票价 {ps}")
            if p.get("requires_booking"):
                extra.append("需预约")
            if p.get("weather_sensitive"):
                extra.append(f"怕雨→备选：{p.get('indoor_backup','室内替代')}")
            if p.get("map_links"):
                extra.append(links_str(p["map_links"]))
            if extra:
                L.append(f"  - {' ｜ '.join(extra)}")
        if day.get("transports"):
            segs = []
            for t in day["transports"]:
                segs.append(f"{t.get('from_idx')}→{t.get('to_idx')} {t.get('mode')} {t.get('duration_min',0):g}min")
            L.append(f"  - 🚇 交通：{'；'.join(segs)}")
        pb = day.get("plan_b")
        if pb:
            pbs = pb if isinstance(pb, list) else [pb]
            for b in pbs:
                L.append(f"  - ☔ Plan B：{b.get('trigger')} → {b.get('alternative')}（{b.get('impact')}）")
        L.append("")

    # 预约清单
    if trip.get("prebook"):
        L.append("## 📋 预约/购票清单")
        for p in trip["prebook"]:
            mark = {"must": "🔴必", "recommended": "🟡建议", "optional": "⚪可选"}.get(p.get("priority"), "")
            L.append(f"- {mark} **{p.get('item')}**　截止：{p.get('deadline')}　状态：{p.get('status')}　[链接]({p.get('url')})")
        L.append("")

    # 预算
    if trip.get("budget_summary"):
        ps = price_str(trip["budget_summary"])
        if ps:
            L.append(f"## 💰 预算概览\n- 合计约 {ps}\n")

    # 安全提醒
    if trip.get("safety_notes"):
        L.append("## ⚠️ 安全与注意事项")
        for s in trip["safety_notes"]:
            icon = {"notice": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(s.get("severity"), "•")
            L.append(f"- {icon} {s.get('risk')} → {s.get('action')}")
        L.append("")

    # 信息源覆盖
    if trip.get("source_coverage"):
        L.append("## 🔎 信息源与核对状态")
        for c in trip["source_coverage"]:
            L.append(f"- **{c.get('platform')}**：{c.get('status')}　（{c.get('purpose')}，核对于 {c.get('checked_at')}）")
        L.append("")

    # 复核
    if trip.get("rechecks"):
        L.append("## 🔁 行前复核")
        for r in trip["rechecks"]:
            L.append(f"- {r.get('item')}（{r.get('category')}）：{r.get('status')}，下次复核 {r.get('recheck_at')}")
        L.append("")

    return "\n".join(L).rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("trip")
    ap.add_argument("-o", "--output", default=None)
    a = ap.parse_args()
    trip = json.load(open(a.trip, encoding="utf-8"))
    md = render(trip)
    if a.output:
        open(a.output, "w", encoding="utf-8").write(md)
        print(f"wrote {a.output} ({len(md)} bytes)")
    else:
        sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
