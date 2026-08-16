"""一次性关键词检索 + 记忆：输入新关键词立即搜，并记入偏好历史。

用法：
    python scripts/search.py "diabetes comorbidity"           # 用该词检索（最近 7 天）
    python scripts/search.py "diabetes comorbidity" --days 30 --top 20
    python scripts/search.py "diabetes comorbidity" --save    # 检索并追加到 config.yaml 的 keywords
"""
from __future__ import annotations

import argparse
import os
import sys

from common import ROOT, load_config, load_json, save_json
import collect
import digest
import journal_metrics


def _append_keyword(kw):
    cfg_path = os.path.join(ROOT, "config", "config.yaml")
    with open(cfg_path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    if any(kw in ln for ln in lines):
        print("该词已在 config.yaml 中，跳过追加。")
        return
    idx = None
    for i, ln in enumerate(lines):
        if ln.strip().startswith("keywords:"):
            idx = i
            break
    if idx is None:
        print("未找到 keywords: 块，请手动添加。")
        return
    lines.insert(idx + 1, '    - "' + kw + '"')
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("已追加关键词到 config.yaml：" + kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help="检索词")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--save", action="store_true", help="把该词追加到 config.yaml 的 keywords")
    args = ap.parse_args()

    cfg = load_config()
    # 一次性检索：只用本次输入词作为检索词（不混入 config 里的方法/数据库）
    cfg.setdefault("profile", {})
    cfg["profile"]["keywords"] = [args.query]
    cfg["profile"]["methods"] = []
    cfg["profile"]["databases"] = []

    recs = collect.collect_all(cfg, args.days)
    seen, ded = set(), []
    for r in recs:
        if r["id"] not in seen:
            seen.add(r["id"])
            ded.append(r)

    journal_metrics.enrich_all(ded)

    prefs_path = os.path.join(ROOT, "config", "preferences.json")
    prefs = load_json(prefs_path, {})
    scored = sorted(((digest.score(r, cfg, prefs), r) for r in ded), key=lambda x: -x[0])
    top = [r for s, r in scored[:args.top] if s > 0]

    # 记忆：记入 keyword_history
    kw_hist = prefs.setdefault("keyword_history", [])
    if args.query and args.query not in kw_hist:
        kw_hist.append(args.query)
    prefs["keyword_history"] = kw_hist[-50:]
    save_json(prefs_path, prefs)

    print(f"检索词：{args.query}　命中 {len(top)} 条（最近 {args.days} 天）\n")
    print(digest.render(top, cfg, prefs))

    if args.save:
        _append_keyword(args.query)
    return 0


if __name__ == "__main__":
    sys.exit(main())
