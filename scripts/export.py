"""把个人文献库导出为 BibTeX / CSV（供 Zotero/EndNote 导入或课题组分享）。

用法：
    python scripts/export.py bibtex   # -> data/library.bib
    python scripts/export.py csv      # -> data/library.csv
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

from common import ROOT, load_config, load_json


def _entries(cfg):
    root = os.path.join(ROOT, cfg.get("archive", {}).get("root", "library"))
    out = []
    if os.path.isdir(root):
        for dirpath, dirs, files in os.walk(root):
            mp = os.path.join(dirpath, "metadata.json")
            if os.path.exists(mp):
                out.append(load_json(mp, {}))
    return out


def _bibkey(meta):
    authors = meta.get("authors") or []
    last = ""
    if authors:
        parts = (authors[0] or "").split()
        last = (parts[-1] if parts else "").replace(" ", "")
    year = meta.get("year") or "0000"
    key = (last[:12] or "Anon") + str(year)
    return "".join(c for c in key if c.isalnum())


def cmd_bibtex(args):
    cfg = load_config()
    entries = _entries(cfg)
    lines = []
    for m in entries:
        authors = " and ".join(m.get("authors") or [])
        key = _bibkey(m)
        lines.append("@article{" + key + ",")
        lines.append("  title = {" + (m.get("title") or "") + "},")
        lines.append("  author = {" + authors + "},")
        if m.get("journal"):
            lines.append("  journal = {" + str(m.get("journal")) + "},")
        if m.get("year"):
            lines.append("  year = {" + str(m.get("year")) + "},")
        if m.get("doi"):
            lines.append("  doi = {" + str(m.get("doi")) + "},")
        if m.get("url"):
            lines.append("  url = {" + str(m.get("url")) + "},")
        lines.append("}")
        lines.append("")
    out = os.path.join(ROOT, "data", "library.bib")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"导出 {len(entries)} 条 → {out}")
    return 0


def cmd_csv(args):
    cfg = load_config()
    entries = _entries(cfg)
    out = os.path.join(ROOT, "data", "library.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["title", "authors", "journal", "year", "doi", "url"])
        for m in entries:
            w.writerow([m.get("title", ""), "; ".join(m.get("authors") or []),
                        m.get("journal", ""), m.get("year", ""),
                        m.get("doi", ""), m.get("url", "")])
    print(f"导出 {len(entries)} 条 → {out}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("bibtex", help="导出 BibTeX").set_defaults(fn=cmd_bibtex)
    sub.add_parser("csv", help="导出 CSV").set_defaults(fn=cmd_csv)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
