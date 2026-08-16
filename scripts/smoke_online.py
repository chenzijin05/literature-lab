"""连通性 + 真实检索自检（不依赖 pyyaml，用于在你自己电脑上定位问题）。

用法：
    python scripts/smoke_online.py

它会：
1. ping 各 API 端点（PubMed/OpenAlex/Crossref/Semantic Scholar）；
2. 用关键词 "cancer" 对 PubMed/OpenAlex/Crossref 各做一次真实小检索，报告条数。
"""
from __future__ import annotations

import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect

UA = {"User-Agent": "literature-lab/0.1"}

ENDPOINTS = {
    "PubMed": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=cancer&retmax=1&retmode=json",
    "OpenAlex": "https://api.openalex.org/works?per-page=1",
    "Crossref": "https://api.crossref.org/works?rows=1",
    "Semantic Scholar": "https://api.semanticscholar.org/graph/v1/paper/search?query=cancer&limit=1",
}


def check_connectivity():
    results = {}
    for name, url in ENDPOINTS.items():
        try:
            req = urllib.request.Request(url, headers=UA)
            urllib.request.urlopen(req, timeout=10)
            results[name] = "OK"
        except Exception as e:
            results[name] = "FAIL: " + str(e)
    return results


def mini_search():
    cfg = {"profile": {"email": "", "keywords": ["cancer"], "methods": []},
           "sources": {"pubmed": {"enabled": True, "max_results": 5},
                       "openalex": {"enabled": True, "max_results": 5},
                       "crossref": {"enabled": True, "max_results": 5}}}
    results = {}
    for name, fn in [("pubmed", collect.pubmed), ("openalex", collect.openalex),
                     ("crossref", collect.crossref)]:
        try:
            recs = fn(cfg, 3)
            results[name] = "OK（" + str(len(recs)) + " 条）"
        except Exception as e:
            results[name] = "FAIL: " + str(e)
    return results


def main():
    print("== 连通性自检 ==")
    for k, v in check_connectivity().items():
        print("  [" + v.split(":")[0] + "] " + k + "  " + v)
    print("== 真实检索自检（关键词 cancer，最近 3 天） ==")
    for k, v in mini_search().items():
        print("  [" + v.split(":")[0] + "] " + k + "  " + v)
    print("提示：全部 FAIL 多为网络/代理问题；连通 OK 但 0 条多为关键词或时间窗问题。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
