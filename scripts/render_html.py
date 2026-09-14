#!/usr/bin/env python3
"""
把 trip.json 渲染为单文件响应式 HTML 攻略（移动端优先，可离线）。
用法：python scripts/render_html.py assets/template.html trip.json -o trip.html

模板中 __TRIP_JSON__ 占位符会被替换为内联 JSON，前端 JS 负责渲染，
因此生成的 HTML 不依赖任何外部 CDN/网络。
"""
from __future__ import annotations
import argparse, json, sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("template")
    ap.add_argument("trip")
    ap.add_argument("-o", "--output", default=None)
    a = ap.parse_args()

    tpl = open(a.template, encoding="utf-8").read()
    trip = json.load(open(a.trip, encoding="utf-8"))
    # 转义 </script> 防止提前闭合
    payload = json.dumps(trip, ensure_ascii=False).replace("</", "<\\/")
    html = tpl.replace("__TRIP_JSON__", payload)

    if a.output:
        open(a.output, "w", encoding="utf-8").write(html)
        print(f"wrote {a.output} ({len(html)} bytes)")
    else:
        sys.stdout.write(html)
    return 0


if __name__ == "__main__":
    sys.exit(main())
