"""管理偏好：like / dislike 主题词，查看当前偏好（供持续优化推送）。

用法：
    python scripts/feedback.py like <主题词...>
    python scripts/feedback.py dislike <主题词...>
    python scripts/feedback.py show
"""
from __future__ import annotations

import argparse
import os
import sys

from common import ROOT, load_json, save_json

PREFS = os.path.join(ROOT, "config", "preferences.json")


def cmd_like(args):
    p = load_json(PREFS, {})
    liked = p.setdefault("liked_topics", [])
    disliked = p.setdefault("disliked_topics", [])
    for t in args.topics:
        if t not in liked:
            liked.append(t)
        disliked = [d for d in disliked if d != t]
    p["disliked_topics"] = disliked
    save_json(PREFS, p)
    print("liked_topics:", p["liked_topics"])
    return 0


def cmd_dislike(args):
    p = load_json(PREFS, {})
    disliked = p.setdefault("disliked_topics", [])
    liked = p.setdefault("liked_topics", [])
    for t in args.topics:
        if t not in disliked:
            disliked.append(t)
        liked = [d for d in liked if d != t]
    p["liked_topics"] = liked
    save_json(PREFS, p)
    print("disliked_topics:", p["disliked_topics"])
    return 0


def cmd_show(args):
    p = load_json(PREFS, {})
    print("liked_topics:", p.get("liked_topics", []))
    print("disliked_topics:", p.get("disliked_topics", []))
    print("keyword_history:", p.get("keyword_history", []))
    print("topic_distribution:", p.get("topic_distribution", {}))
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("like", help="喜欢某主题词（加权）")
    p1.add_argument("topics", nargs="+")
    p1.set_defaults(fn=cmd_like)
    p2 = sub.add_parser("dislike", help="不喜欢某主题词（降权）")
    p2.add_argument("topics", nargs="+")
    p2.set_defaults(fn=cmd_dislike)
    p3 = sub.add_parser("show", help="查看当前偏好")
    p3.set_defaults(fn=cmd_show)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
