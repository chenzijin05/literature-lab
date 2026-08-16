"""下载并合并期刊指标数据 → data/journal_metrics.csv（影响因子 + JCR 分区 + 中科院分区）。

数据源（开源镜像，供个人/课题组研究使用，请尊重原始数据版权）：
- 中科院分区表 2025（2025-03-20 发布）：IvyScience/journalQuartile 的 FQBJCR2025-UTF8.csv
- JCR 影响因子（JIF 2024）+ JCR 分区：theabhijitdn/WoS-JCR-Impact-Factor-Explorer-2025

下载走 git blobs API（api.github.com），比 raw.githubusercontent.com 更稳；
API 失败时自动回退到 raw 链接。

用法：
    python scripts/fetch_journal_metrics.py
"""
from __future__ import annotations

import base64
import csv
import json
import os
import re
import urllib.request

from common import ROOT, DATA_DIR

CAS_REPO, CAS_BRANCH, CAS_PATH = ("IvyScience/journalQuartile", "master",
                                   "中科院分区表及JCR原始数据文件/FQBJCR2025-UTF8.csv")
CAS_RAW = ("https://raw.githubusercontent.com/IvyScience/journalQuartile/master/"
           "%E4%B8%AD%E7%A7%91%E9%99%A2%E5%88%86%E5%8C%BA%E8%A1%A8%E5%8F%8AJCR%E5%8E%9F%E5%A7%8B%E6%95%B0%E6%8D%AE%E6%96%87%E4%BB%B6/"
           "FQBJCR2025-UTF8.csv")
JCR_REPO, JCR_BRANCH, JCR_PATH = ("theabhijitdn/WoS-JCR-Impact-Factor-Explorer-2025", "main",
                                  "JCR_Enriched_With_ISSN_Matching.csv")
JCR_RAW = ("https://raw.githubusercontent.com/theabhijitdn/WoS-JCR-Impact-Factor-Explorer-2025/"
           "main/JCR_Enriched_With_ISSN_Matching.csv")


def _get_json(url, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": "literature-lab/0.1",
                                                "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _download_via_api(repo, branch, path):
    """通过 git blobs API 下载（比 raw.githubusercontent 更稳）。"""
    tree = _get_json("https://api.github.com/repos/%s/git/trees/%s?recursive=1" % (repo, branch))
    sha = None
    for it in tree.get("tree", []):
        if it["path"] == path:
            sha = it["sha"]
            break
    if not sha:
        raise RuntimeError("在仓库中找不到 " + path)
    blob = _get_json("https://api.github.com/repos/%s/git/blobs/%s" % (repo, sha), timeout=300)
    return base64.b64decode(blob["content"]).decode("utf-8-sig", "replace")


def _download(repo, branch, path, raw_url):
    try:
        print("  通过 git blobs API 下载（可能需几十秒）...")
        return _download_via_api(repo, branch, path)
    except Exception as e:
        print("  API 下载失败（%s），回退 raw 链接 ..." % e)
        req = urllib.request.Request(raw_url, headers={"User-Agent": "literature-lab/0.1"})
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.read().decode("utf-8-sig", "replace")


def _find_col(header, *keywords):
    for i, h in enumerate(header):
        hl = (h or "").strip().lower()
        for kw in keywords:
            if kw in hl:
                return i
    return None


def _find_col_exact(header, *names):
    names = [n.strip().lower() for n in names]
    for i, h in enumerate(header):
        if (h or "").strip().lower() in names:
            return i
    return None


def _find_if_col(header):
    """精确定位影响因子列：优先匹配 "JIF 2024" 这类「JIF+年份」，排除 JIF Quartile 等。"""
    for i, h in enumerate(header):
        hl = (h or "").strip().lower()
        if re.search(r"jif\s*\d{4}", hl) and "quartile" not in hl:
            return i
    return _find_col(header, "impact factor", "影响因子") or _find_col_exact(header, "if")


def _clean_issn(v):
    m = re.search(r"\d{4}-?\d{3}[0-9Xx]", str(v or "").upper())
    return m.group(0) if m else (v or "").strip()


def _clean_partition(v):
    m = re.search(r"(\d)\s*区?", str(v or ""))
    return (m.group(1) + "区") if m else (v or "").strip()


def _clean_quartile(v):
    m = re.search(r"Q\s*([1-4])", str(v or "").upper())
    return ("Q" + m.group(1)) if m else (v or "").strip()


def _parse_cas(text):
    rows = list(csv.reader(text.splitlines()))
    if not rows:
        return {}
    header = rows[0]
    i_name = _find_col(header, "期刊名称", "journal", "刊名")
    i_issn = _find_col(header, "issn")
    i_part = _find_col(header, "分区")
    print("[CAS] 表头:", header)
    print("[CAS] 列映射: name=%s issn=%s partition=%s" % (i_name, i_issn, i_part))
    out = {}
    for r in rows[1:]:
        if not r:
            continue
        def g(i):
            return r[i] if (i is not None and i < len(r)) else ""
        issn = _clean_issn(g(i_issn))
        name = g(i_name).strip() if i_name is not None else ""
        part = _clean_partition(g(i_part)) if i_part is not None else ""
        if issn:
            out.setdefault(issn, {"journal": name, "cas_partition": part})
        if name:
            out.setdefault("N:" + name.lower(), {"journal": name, "cas_partition": part})
    return out


def _parse_jcr(text):
    rows = list(csv.reader(text.splitlines()))
    if not rows:
        return {}
    header = rows[0]
    i_name = _find_col(header, "journal name", "journal", "期刊名称")
    i_issn = _find_col(header, "issn")
    i_q = _find_col(header, "quartile") or _find_col_exact(header, "q")
    i_if = _find_if_col(header)
    print("[JCR] 表头:", header)
    print("[JCR] 列映射: name=%s issn=%s if=%s q=%s" % (i_name, i_issn, i_if, i_q))
    out = {}
    for r in rows[1:]:
        if not r:
            continue
        def g(i):
            return r[i] if (i is not None and i < len(r)) else ""
        issn = _clean_issn(g(i_issn))
        name = g(i_name).strip() if i_name is not None else ""
        ifv = g(i_if).strip() if i_if is not None else ""
        q = _clean_quartile(g(i_q)) if i_q is not None else ""
        if issn:
            out.setdefault(issn, {"journal": name, "impact_factor": ifv, "jcr_quartile": q})
        if name:
            out.setdefault("N:" + name.lower(), {"journal": name, "impact_factor": ifv, "jcr_quartile": q})
    return out


def main():
    print("下载 JCR 数据 ...")
    jcr = _parse_jcr(_download(JCR_REPO, JCR_BRANCH, JCR_PATH, JCR_RAW))
    print("下载中科院数据 ...")
    cas = _parse_cas(_download(CAS_REPO, CAS_BRANCH, CAS_PATH, CAS_RAW))

    merged = {}
    for key, e in cas.items():
        merged.setdefault(key, {}).update(e)
    for key, e in jcr.items():
        merged.setdefault(key, {}).update(e)

    out_path = os.path.join(DATA_DIR, "journal_metrics.csv")
    os.makedirs(DATA_DIR, exist_ok=True)
    n = 0
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["issn", "journal", "impact_factor", "jcr_quartile", "cas_partition"])
        for key, e in merged.items():
            issn = "" if key.startswith("N:") else key
            w.writerow([issn, e.get("journal", ""),
                        e.get("impact_factor", ""),
                        e.get("jcr_quartile", ""),
                        e.get("cas_partition", "")])
            n += 1
    print(f"合并完成：{n} 条期刊指标 → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
