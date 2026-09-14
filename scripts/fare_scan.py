#!/usr/bin/env python3
"""
fare-scan：找「最便宜怎么飞」的比价扫描器。

目标不是排行程，而是在给定出行窗口内，把「直飞 + 各中转枢纽 × 多个候选日期」的
往返组合全部列出，为每一段生成比价链接；本地读到实价后按总价从低到高排名，
直接告诉你最便宜的飞法。

两个子命令：
  plan  生成扫描计划（确定性，可离线跑）：枚举组合 + 每段查询链接
  rank  读入已填价的结果文件，按总价排名，输出最便宜组合

用法：
  python scripts/fare_scan.py plan --from PVG --to MLE \
      --window-start 2026-09-25 --window-end 2026-10-07 \
      --min-stay 5 --hubs KUL,BKK,SIN --hub-stay 3 --adults 2 [--direct] -o plan.json

  # 本地用浏览器把 plan.json 里每段的 price.min 填好后：
  python scripts/fare_scan.py rank --results plan.filled.json

纯标准库；plan 复用 build_links.flight_links。
"""
from __future__ import annotations
import argparse, datetime, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_links import flight_links  # noqa: E402

HUB_NAMES = {"KUL": "吉隆坡", "BKK": "曼谷", "SIN": "新加坡", "DMK": "曼谷廊曼",
             "HKG": "香港", "SGN": "胡志明", "CMB": "科伦坡"}


def d(s: str) -> datetime.date:
    return datetime.date.fromisoformat(s)


def ds(x: datetime.date) -> str:
    return x.isoformat()


def _out_dates(start, end, min_total, step, cap):
    outs, cur = [], start
    while cur + datetime.timedelta(days=min_total) <= end:
        outs.append(cur)
        cur += datetime.timedelta(days=step)
    return outs[:cap]


def _leg(leg, o, dest, date, adults):
    return {"leg": leg, "from": o, "to": dest, "date": ds(date),
            "links": flight_links(o, dest, ds(date), None, adults),
            "price": {"min": None, "currency": "CNY", "unit": "人"}}


def build_plan(args) -> dict:
    start, end = d(args.window_start), d(args.window_end)
    adults = args.adults
    combos = []

    # 直飞
    if args.direct:
        for i, o in enumerate(_out_dates(start, end, args.min_stay, args.step, args.max_dates), 1):
            ret = o + datetime.timedelta(days=args.min_stay)
            combos.append({
                "id": f"DIRECT-{i}", "routing": f"{args.origin}⇄{args.dest} 直飞",
                "hub": None, "dest_stay": args.min_stay,
                "legs": [_leg("outbound", args.origin, args.dest, o, adults),
                         _leg("return", args.dest, args.origin, ret, adults)],
                "total_min": None,
            })

    # 中转枢纽
    for hub in [h.strip().upper() for h in args.hubs.split(",") if h.strip()]:
        min_total = args.hub_stay + args.min_stay
        for i, o in enumerate(_out_dates(start, end, min_total, args.step, args.max_dates), 1):
            to_dest = o + datetime.timedelta(days=args.hub_stay)
            ret = to_dest + datetime.timedelta(days=args.min_stay)
            hn = HUB_NAMES.get(hub, hub)
            combos.append({
                "id": f"{hub}-{i}",
                "routing": f"{args.origin}→{hub}→{args.dest}（中转{hn}，玩{args.hub_stay}天）",
                "hub": hub, "hub_stay": args.hub_stay, "dest_stay": args.min_stay,
                "legs": [_leg("outbound", args.origin, hub, o, adults),
                         _leg("internal", hub, args.dest, to_dest, adults),
                         _leg("return", args.dest, args.origin, ret, adults)],
                "total_min": None,
            })

    return {
        "params": {
            "origin": args.origin, "dest": args.dest,
            "window": [args.window_start, args.window_end],
            "min_stay": args.min_stay, "hub_stay": args.hub_stay,
            "hubs": args.hubs, "adults": adults, "direct": args.direct,
        },
        "note": "拆票（分段购买）通常比联程便宜；每段 price.min 请用浏览器读价填入（单位：元/人），再用 rank 排名。",
        "combos": combos,
    }


def rank(results: dict) -> str:
    adults = results.get("params", {}).get("adults", 1)
    rows = []
    for c in results.get("combos", []):
        legs = c.get("legs", [])
        prices = [(l.get("price") or {}).get("min") for l in legs]
        if any(p is None for p in prices):
            rows.append((None, c, "缺价"))
            continue
        per = sum(prices)
        rows.append((per, c, "ok"))

    priced = sorted([r for r in rows if r[0] is not None], key=lambda x: x[0])
    missing = [r for r in rows if r[0] is None]

    out = ["# fare-scan 排名（按单人总价升序）\n"]
    if not priced:
        out.append("（暂无已填价组合，请先用浏览器读价填 price.min）")
    for rank_i, (per, c, _) in enumerate(priced, 1):
        legdesc = " + ".join(
            f"{l['from']}→{l['to']} {l['date']} ¥{(l.get('price') or {}).get('min')}" for l in c["legs"])
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank_i, f"{rank_i}.")
        out.append(f"{medal} **{c['routing']}**")
        out.append(f"   单人 ¥{per}　×{adults}人 = ¥{per*adults}")
        out.append(f"   {legdesc}\n")
    if missing:
        out.append("## 待补价组合")
        for _, c, _s in missing:
            out.append(f"- {c['id']} {c['routing']}")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan")
    p.add_argument("--from", dest="origin", required=True)
    p.add_argument("--to", dest="dest", required=True)
    p.add_argument("--window-start", required=True)
    p.add_argument("--window-end", required=True)
    p.add_argument("--min-stay", type=int, required=True, help="目的地停留天数（下限）")
    p.add_argument("--hubs", default="KUL,BKK,SIN")
    p.add_argument("--hub-stay", type=int, default=3, help="中转城市停留天数")
    p.add_argument("--adults", type=int, default=1)
    p.add_argument("--direct", action="store_true", help="同时纳入直飞对比")
    p.add_argument("--step", type=int, default=2, help="候选出发日步长（天）")
    p.add_argument("--max-dates", type=int, default=4, help="每条路由最多候选出发日")
    p.add_argument("-o", "--output", default=None)

    r = sub.add_parser("rank")
    r.add_argument("--results", required=True)

    a = ap.parse_args()
    if a.cmd == "plan":
        plan = build_plan(a)
        s = json.dumps(plan, ensure_ascii=False, indent=2)
        if a.output:
            open(a.output, "w", encoding="utf-8").write(s)
            print(f"wrote {a.output}; combos={len(plan['combos'])}")
        else:
            print(s)
    elif a.cmd == "rank":
        results = json.load(open(a.results, encoding="utf-8"))
        print(rank(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
