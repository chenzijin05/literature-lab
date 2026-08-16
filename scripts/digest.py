"""生成每日文献摘要：去重、偏好打分排序、防信息茧房提示。

用法：
    python scripts/digest.py            # 重新检索并生成今日摘要
    python scripts/digest.py --offline  # 读 data/raw.jsonl（不联网）生成摘要
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import sys

from common import (ROOT, DATA_DIR, load_config, load_json, save_json, now_iso)
import collect
import journal_metrics


def _age_days(item) -> int:
    pd = item.get("published_date") or ""
    try:
        d = dt.date.fromisoformat(pd[:10])
        return max(0, (dt.date.today() - d).days)
    except Exception:
        return 30


def score(item, cfg, prefs) -> float:
    p = cfg.get("profile", {})
    text = ((item.get("title") or "") + " " + (item.get("abstract") or "")).lower()
    s = 0.0
    for kw in p.get("keywords", []):
        if kw and kw.lower() in text:
            s += 3.0
    for m in p.get("methods", []):
        if m and m.lower() in text:
            s += 4.0
    for db in p.get("databases", []):
        if db and db.lower() in text:
            s += 2.0
    for nk in p.get("negative_keywords", []):
        if nk and nk.lower() in text:
            s -= 10.0
    s += max(0.0, 5.0 - _age_days(item) * 0.3)
    if item.get("journal_tier") == "Q1":
        s += 2.0
    c = item.get("citations") or 0
    if c:
        s += min(3.0, math.log10(c + 1))
    for t in prefs.get("liked_topics", []):
        if t and t.lower() in text:
            s += 1.5
    for t in prefs.get("disliked_topics", []):
        if t and t.lower() in text:
            s -= 4.0
    # 搜索历史（记忆）轻微加权
    for t in (prefs.get("keyword_history") or [])[-10:]:
        if t and t.lower() in text:
            s += 0.5
    return round(s, 2)


def _matches_interest(item, cfg) -> bool:
    """判断文献是否命中当前关键词/方法/数据库（用于探索性推荐）。"""
    p = cfg.get("profile", {}) or {}
    text = ((item.get("title") or "") + " " + (item.get("abstract") or "")).lower()
    for kw in (p.get("keywords") or []) + (p.get("methods") or []) + (p.get("databases") or []):
        if kw and kw.lower() in text:
            return True
    return False


def suggest_keywords(items, cfg, prefs, k=5):
    """从当前批次的概念词里挑出用户尚未覆盖的高频词，供持续优化关键词。"""
    p = cfg.get("profile", {}) or {}
    existing = set()
    for e in (p.get("keywords") or []) + (p.get("methods") or []):
        existing.add(e.strip().lower())
    counts = {}
    for it in items:
        for kw in (it.get("keywords") or []):
            kw = kw.strip()
            if kw and kw.lower() not in existing:
                counts[kw] = counts.get(kw, 0) + 1
    return [w for w, _ in sorted(counts.items(), key=lambda x: -x[1])[:k]]


def anti_bubble_section(prefs, cfg, items, suggested=None) -> str:
    interval = int(cfg.get("anti_bubble", {}).get("interval_days", 7))
    last = prefs.get("last_explore_prompt")
    if last:
        try:
            d = dt.date.fromisoformat(str(last)[:10])
            if (dt.date.today() - d).days < interval:
                return ""
        except Exception:
            pass
    prefs["last_explore_prompt"] = dt.date.today().isoformat()
    sugg = cfg.get("anti_bubble", {}).get("suggest_keywords", []) or []
    dist = {}
    for it in items:
        for kw in (it.get("keywords") or [])[:3]:
            dist[kw] = dist.get(kw, 0) + 1
    top = sorted(dist.items(), key=lambda x: -x[1])[:5]
    lines = ["---", "", "## 防信息茧房提示（每 " + str(interval) + " 天）", ""]
    if top:
        lines.append("最近检索的主题分布（前 5）：")
        for k, v in top:
            lines.append(f"- {k}：{v} 篇")
        lines.append("")
    if sugg:
        lines.append("建议补充邻域/反向关键词，扩大检索面：")
        for s in sugg:
            lines.append(f"- {s}")
        lines.append("")
    if suggested:
        lines.append("自动发现的相关主题词（可加进 keywords 持续优化）：")
        for s in suggested:
            lines.append(f"- {s}")
        lines.append("")
    lines.append("> 若推送开始雷同，请到 config/config.yaml 增加新的 keywords / methods，或换用反向词（如把「预后」换成「机制」「干预」）。")
    return "\n".join(lines)


def render(items, cfg, prefs, serendipity_ids=None) -> str:
    p = cfg.get("profile", {})
    today = dt.date.today().isoformat()
    lines = ["# 文献日报 " + today, "",
             "研究者：" + str(p.get("researcher", "")) + "　关键词：" + "、".join(p.get("keywords", [])), ""]
    if not items:
        lines.append("今日无新增文献。")
        return "\n".join(lines)
    for i, it in enumerate(items, 1):
        title = it.get("title") or "(无标题)"
        journal = it.get("journal") or ""
        year = it.get("year") or ""
        src = it.get("source") or ""
        url = it.get("url") or ""
        pdf = it.get("pdf_url") or ""
        doi = it.get("doi") or ""
        c = it.get("citations")
        authors = ", ".join((it.get("authors") or [])[:5])
        lines.append(f"## {i}. {title}")
        if serendipity_ids and it.get("id") in serendipity_ids:
            lines.append("> ✨ 探索推荐：与当前关键词无关，用于打破信息茧房")
        lines.append(f"- 期刊：{journal}（{year}）　来源：{src}")
        metrics = []
        if it.get("impact_factor"):
            metrics.append("IF " + str(it.get("impact_factor")))
        if it.get("jcr_quartile"):
            metrics.append("JCR " + str(it.get("jcr_quartile")))
        if it.get("cas_partition"):
            metrics.append("中科院 " + str(it.get("cas_partition")))
        if metrics:
            lines.append("- 期刊指标：" + " | ".join(metrics))
        if authors:
            lines.append(f"- 作者：{authors}")
        if doi:
            lines.append(f"- DOI：{doi}")
        if url:
            lines.append(f"- 链接：{url}")
        if pdf:
            lines.append(f"- PDF：{pdf}")
        if c is not None:
            lines.append(f"- 被引：{c}")
        ab = (it.get("abstract") or "")[:400]
        if ab:
            lines.append(f"- 摘要：{ab}" + ("…" if len((it.get("abstract") or "")) > 400 else ""))
        lines.append("")
    return "\n".join(lines)


def _notify(cfg, md, title):
    """可选：把日报推送到 webhook（企业微信/钉钉/通用）。"""
    n = cfg.get("notify", {}) or {}
    if not (n.get("enabled") and n.get("webhook_url")):
        return
    import urllib.request
    typ = n.get("type", "generic")
    body = md[:4000]
    if typ == "wecom":
        payload = json.dumps({"msgtype": "markdown", "markdown": {"content": body}})
    elif typ == "dingtalk":
        payload = json.dumps({"msgtype": "markdown", "markdown": {"title": title, "text": body}})
    else:
        payload = json.dumps({"content": body})
    req = urllib.request.Request(n["webhook_url"], data=payload.encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=15)
        print("[notify] 已推送")
    except Exception as e:
        print(f"[notify] 推送失败: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="读 data/raw.jsonl，不重新检索")
    ap.add_argument("--since", type=int, default=None)
    args = ap.parse_args()

    cfg = load_config()
    prefs_path = os.path.join(ROOT, "config", "preferences.json")
    prefs = load_json(prefs_path, {})
    seen_path = os.path.join(DATA_DIR, "seen.json")
    seen = load_json(seen_path, {})

    if args.offline:
        raw_path = os.path.join(DATA_DIR, "raw.jsonl")
        recs = []
        if os.path.exists(raw_path):
            with open(raw_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        recs.append(json.loads(line))
    else:
        since = args.since if args.since is not None else cfg.get("schedule", {}).get("since_days", 7)
        recs = collect.collect_all(cfg, since)
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(os.path.join(DATA_DIR, "raw.jsonl"), "w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    journal_metrics.enrich_all(recs)

    fresh = [r for r in recs if r["id"] not in seen]
    scored = [(score(r, cfg, prefs), r) for r in fresh]
    scored.sort(key=lambda x: -x[0])
    top_n = int(cfg.get("digest", {}).get("top_n", 20))
    top = [r for s, r in scored[:top_n] if s > 0]

    # 探索性推荐：分数>0 但不匹配当前关键词/方法/数据库，用于打破信息茧房
    serendipity_n = int(cfg.get("digest", {}).get("serendipity", 2))
    top_ids = {r["id"] for r in top}
    serendipity = []
    if serendipity_n > 0:
        for s, r in scored:
            if len(serendipity) >= serendipity_n:
                break
            if r["id"] in top_ids or s <= 0:
                continue
            if not _matches_interest(r, cfg):
                serendipity.append(r)
    top = top + serendipity
    serendipity_ids = {r["id"] for r in serendipity}

    for r in top:
        seen[r["id"]] = now_iso()
    save_json(seen_path, seen)

    candidates = [r for s, r in scored[:top_n]]
    suggested = suggest_keywords(candidates, cfg, prefs) if top else []
    ab = anti_bubble_section(prefs, cfg, candidates, suggested) if top else ""
    md = render(top, cfg, prefs, serendipity_ids) + "\n" + ab + "\n"

    out_dir = cfg.get("digest", {}).get("output_dir", "digest")
    out_path = os.path.join(ROOT, out_dir, dt.date.today().isoformat() + ".md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)

    _notify(cfg, md, "文献日报 " + dt.date.today().isoformat())

    prefs["last_run"] = now_iso()
    prefs["seen_count"] = len(seen)
    # 持续优化：记录关键词历史 + 主题分布
    kw_hist = prefs.setdefault("keyword_history", [])
    for kw in (cfg.get("profile", {}) or {}).get("keywords", []) or []:
        if kw and kw not in kw_hist:
            kw_hist.append(kw)
    prefs["keyword_history"] = kw_hist[-50:]
    dist = prefs.setdefault("topic_distribution", {})
    for it in candidates:
        for kw in (it.get("keywords") or [])[:3]:
            dist[kw] = dist.get(kw, 0) + 1
    save_json(prefs_path, prefs)

    print(f"生成 {out_path}，推送 {len(top)} 条（其中探索 {len(serendipity)} 条）")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
