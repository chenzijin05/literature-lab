"""取论文材料，生成中英对照结构化总结脚手架（可选 --auto 调 LLM 自动填充）。

用法：
    python scripts/summarize.py prep <doi|本地PDF路径> [--auto]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

from common import ROOT, load_config, norm_record, slugify
import archive


def _extract_pdf_text(path):
    try:
        from pdfminer.high_level import extract_text
        return extract_text(path)
    except ImportError:
        return "[未安装 pdfminer.six，无法抽取 PDF 文本；请手动粘贴摘要/全文]"
    except Exception as e:
        return f"[PDF 抽取失败：{e}]"


def _llm_fill(cfg, prompt):
    llm = cfg.get("llm", {}) or {}
    if not (llm.get("api_base") and llm.get("api_key") and llm.get("model")):
        print("未配置 llm（config.yaml 的 llm 段），跳过 --auto。")
        return ""
    url = llm["api_base"].rstrip("/") + "/chat/completions"
    body = json.dumps({"model": llm["model"],
                       "messages": [{"role": "user", "content": prompt}]}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + llm["api_key"]})
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def cmd_prep(args):
    cfg = load_config()
    target = args.target
    if os.path.isfile(target):
        stem = os.path.splitext(os.path.basename(target))[0]
        meta = norm_record({"title": stem.replace("_", " "), "doi": "", "year": None,
                            "journal": "", "authors": [], "url": "", "pdf_url": ""}, "local")
        text = _extract_pdf_text(target)
    else:
        meta = archive.lookup_by_doi(target)
        text = meta.get("abstract", "") or ""
        if meta.get("pdf_url"):
            text += "\n\n[PDF] " + meta["pdf_url"]

    slug = slugify(meta["title"])
    tpl = open(os.path.join(ROOT, "templates", "summary-bilingual.md"), encoding="utf-8").read()
    out = (tpl
           .replace("{title}", meta.get("title", ""))
           .replace("{journal}", meta.get("journal", ""))
           .replace("{year}", str(meta.get("year") or ""))
           .replace("{doi}", meta.get("doi", ""))
           .replace("{pmid}", meta.get("pmid", ""))
           .replace("{url}", meta.get("url", ""))
           .replace("{pdf_url}", meta.get("pdf_url", "")))
    out += "\n\n## 原文材料（供 Agent 精读）\n\n" + text[:8000] + "\n"

    dest = os.path.join(ROOT, "digest", "summaries", slug + ".md")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(out)

    if args.auto:
        prompt = ("请按下方中英对照模板，用中文和英文分别填写「方法/结果/数据库与数据类型/创新点/不足/为何发此刊」。"
                  "严格保留模板结构。原文材料：\n\n" + text[:6000])
        filled = _llm_fill(cfg, prompt)
        if filled:
            with open(dest, "a", encoding="utf-8") as f:
                f.write("\n\n## LLM 自动填充（需人工复核）\n\n" + filled + "\n")

    print(f"总结脚手架 → {dest}")
    print("请用 Agent 按模板填写中英对照各节，然后 archive.py add 入库。")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prep", help="生成中英对照总结脚手架")
    p.add_argument("target")
    p.add_argument("--auto", action="store_true", help="调用 llm 自动填充（需配置 api）")
    p.set_defaults(fn=cmd_prep)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
