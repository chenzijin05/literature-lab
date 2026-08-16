"""归档论文到个人文献库 + book-to-skill 化 + 抽取方法复现代码。

用法：
    python scripts/archive.py add <doi|本地PDF路径>
    python scripts/archive.py index
    python scripts/archive.py skill <slug>
    python scripts/archive.py methods
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys
import urllib.parse

from common import (ROOT, load_config, load_json, save_json, http_get_json,
                    norm_record, slugify, strip_tags)

TB = chr(96)          # 反引号字符
FENCE = TB * 3        # 三个反引号 = 代码围栏

NOTES_TEMPLATE = ("# {title}\n\n## 一句话\n\n\n## 统计方法 / 模型\n\n\n"
                  "## 数据（数据库 / 类型 / 规模）\n\n\n## 关键结果\n\n\n"
                  "## 创新点 / 不足\n\n\n## 为何发此刊\n\n\n## 复现代码\n\n"
                  + FENCE + "python\n\n" + FENCE + "\n")


def _skill_name(meta):
    """生成合法的 book-to-skill name（仅字母/数字/连字符）。"""
    words = re.findall(r"[A-Za-z0-9]+", meta.get("title", "") or "")
    base = "-".join(words[:6]).lower() if words else ("paper-" + (meta.get("id") or "x")[:10])
    name = "paper-" + base if not base.startswith("paper-") else base
    return name[:50].rstrip("-")


def _cfg():
    return load_config()


def lookup_by_doi(doi):
    """用 Crossref 取一篇论文的元数据。"""
    doi = doi.replace("https://doi.org/", "").strip()
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
    data = http_get_json(url).get("message", {})
    title = (data.get("title") or [""])[0]
    dp = (data.get("published") or {}).get("date-parts", [[None]])
    year = dp[0][0] if dp and dp[0] and dp[0][0] else None
    journal = (data.get("container-title") or [""])[0]
    pdf = ""
    for link in (data.get("link") or []):
        if link.get("content-type") == "application/pdf":
            pdf = link.get("URL", "")
            break
    return norm_record({
        "title": title,
        "abstract": strip_tags(data.get("abstract") or ""),
        "authors": [(a.get("given", "") + " " + a.get("family", "")).strip() for a in (data.get("author") or [])],
        "year": year,
        "journal": journal,
        "doi": doi,
        "url": "https://doi.org/" + doi,
        "pdf_url": pdf,
        "published_date": "-".join(str(x) for x in (dp[0] if dp else []) if x),
    }, "crossref")


def cmd_add(args):
    cfg = _cfg()
    root = os.path.join(ROOT, cfg.get("archive", {}).get("root", "library"))
    target = args.target
    pdf_path = None
    if os.path.isfile(target):
        pdf_path = target
        stem = os.path.splitext(os.path.basename(target))[0]
        meta = norm_record({"title": stem.replace("_", " ").replace("-", " "),
                            "doi": "", "year": dt.date.today().year, "journal": "", "authors": []}, "local")
    elif target.startswith("10.") or "doi.org" in target:
        meta = lookup_by_doi(target)
    else:
        print("无法识别的目标：请给 DOI（如 10.1038/s41586-...）或本地 PDF 路径。")
        return 1
    slug = slugify(meta["title"])
    year = meta.get("year") or dt.date.today().year
    dest = os.path.join(root, str(year), slug)
    os.makedirs(dest, exist_ok=True)
    save_json(os.path.join(dest, "metadata.json"), meta)
    with open(os.path.join(dest, "abstract.txt"), "w", encoding="utf-8") as f:
        f.write(meta.get("abstract", "") or "")
    notes_path = os.path.join(dest, "notes.md")
    if not os.path.exists(notes_path):
        with open(notes_path, "w", encoding="utf-8") as f:
            f.write(NOTES_TEMPLATE.replace("{title}", meta.get("title", "")))
    if pdf_path and os.path.isfile(pdf_path):
        shutil.copy2(pdf_path, os.path.join(dest, "paper.pdf"))
    print(f"已归档到 {dest}")
    return cmd_index(args)


def cmd_index(args):
    cfg = _cfg()
    root = os.path.join(ROOT, cfg.get("archive", {}).get("root", "library"))
    index_path = os.path.join(ROOT, cfg.get("archive", {}).get("index", "data/index.json"))
    entries = []
    if os.path.isdir(root):
        for dirpath, dirs, files in os.walk(root):
            meta_path = os.path.join(dirpath, "metadata.json")
            if os.path.exists(meta_path):
                meta = load_json(meta_path, {})
                notes_path = os.path.join(dirpath, "notes.md")
                entries.append({
                    "slug": os.path.basename(dirpath),
                    "rel": os.path.relpath(dirpath, ROOT).replace("\\", "/"),
                    "title": meta.get("title", ""),
                    "doi": meta.get("doi", ""),
                    "year": meta.get("year"),
                    "journal": meta.get("journal", ""),
                    "has_notes": os.path.exists(notes_path),
                    "has_pdf": os.path.exists(os.path.join(dirpath, "paper.pdf")),
                })
    save_json(index_path, entries)
    print(f"索引 {len(entries)} 篇 → {index_path}")
    return 0


def cmd_skill(args):
    cfg = _cfg()
    root = os.path.join(ROOT, cfg.get("archive", {}).get("root", "library"))
    slug = args.slug
    target_dir = None
    for dirpath, dirs, files in os.walk(root):
        if os.path.basename(dirpath) == slug:
            target_dir = dirpath
            break
    if not target_dir:
        print(f"未找到 slug={slug}（先 archive.py add 入库）")
        return 1
    meta = load_json(os.path.join(target_dir, "metadata.json"), {})
    notes_path = os.path.join(target_dir, "notes.md")
    notes = open(notes_path, encoding="utf-8").read() if os.path.exists(notes_path) else ""

    def section(prefix):
        pat = re.compile(r"##\s*" + re.escape(prefix) + r"[^\n]*\n(.*?)(?=\n## |\Z)", re.S)
        m = pat.search(notes)
        return m.group(1).strip() if m else ""

    one = section("一句话")
    methods = section("统计方法")
    data = section("数据")
    results = section("关键结果")
    innov = section("创新点")
    why = section("为何发此刊")
    code = section("复现代码")

    title = re.sub(r'[\r\n"]', " ", meta.get("title", "") or "").strip()
    name = _skill_name(meta)

    tpl_path = os.path.join(ROOT, "templates", "paper-skill-template.md")
    tpl = open(tpl_path, encoding="utf-8").read()
    out = (tpl
           .replace("{name}", name)
           .replace("{title}", title)
           .replace("{journal}", meta.get("journal", ""))
           .replace("{year}", str(meta.get("year") or ""))
           .replace("{doi}", meta.get("doi", ""))
           .replace("{one_liner}", one)
           .replace("{methods}", methods)
           .replace("{data}", data)
           .replace("{results}", results)
           .replace("{innovation_limitations}", innov)
           .replace("{why_journal}", why)
           .replace("{repro_code}", code))
    dest = os.path.join(target_dir, "SKILL.md")
    with open(dest, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"已生成 book-to-skill → {dest}")
    return 0


def cmd_methods(args):
    cfg = _cfg()
    root = os.path.join(ROOT, cfg.get("archive", {}).get("root", "library"))
    out_path = os.path.join(ROOT, cfg.get("archive", {}).get("methods_index", "data/methods.json"))
    methods = []
    for dirpath, dirs, files in os.walk(root):
        notes_path = os.path.join(dirpath, "notes.md")
        if not os.path.exists(notes_path):
            continue
        meta = load_json(os.path.join(dirpath, "metadata.json"), {})
        notes = open(notes_path, encoding="utf-8").read()
        m = re.search(r"##\s*统计方法[^\n]*\n(.*?)(?=\n## |\Z)", notes, re.S)
        method_text = m.group(1).strip() if m else ""
        codes = re.findall(FENCE + r"(?:python|py)?\s*\n(.*?)" + FENCE, notes, re.S)
        methods.append({
            "slug": os.path.basename(dirpath),
            "title": meta.get("title", ""),
            "doi": meta.get("doi", ""),
            "year": meta.get("year"),
            "method_text": method_text[:2000],
            "code_snippets": [c.strip() for c in codes],
        })
    save_json(out_path, methods)
    print(f"方法索引 {len(methods)} 篇 → {out_path}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_add = sub.add_parser("add", help="归档一篇论文（DOI 或本地 PDF）")
    p_add.add_argument("target")
    p_add.set_defaults(fn=cmd_add)
    p_idx = sub.add_parser("index", help="重建 data/index.json")
    p_idx.set_defaults(fn=cmd_index)
    p_sk = sub.add_parser("skill", help="把一篇精读转成 book-to-skill SKILL.md")
    p_sk.add_argument("slug")
    p_sk.set_defaults(fn=cmd_skill)
    p_m = sub.add_parser("methods", help="抽取统计方法+复现代码 → data/methods.json")
    p_m.set_defaults(fn=cmd_methods)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
