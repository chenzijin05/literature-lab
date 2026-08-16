"""期刊指标本地查找 + 富化（影响因子 / JCR 分区 / 中科院分区）。

数据文件 data/journal_metrics.csv，列为：
    issn, journal, impact_factor, jcr_quartile, cas_partition
由 scripts/fetch_journal_metrics.py 下载生成，也可手工编辑更新。
"""
from __future__ import annotations

import csv
import os

from common import ROOT


def _norm(s):
    return (s or "").strip().lower()


def load(path=None):
    """返回 (by_issn, by_name) 两个查找表。"""
    path = path or os.path.join(ROOT, "data", "journal_metrics.csv")
    by_issn, by_name = {}, {}
    if not os.path.exists(path):
        return by_issn, by_name
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            issn = _norm(row.get("issn", ""))
            name = _norm(row.get("journal", ""))
            entry = {
                "impact_factor": (row.get("impact_factor") or "").strip(),
                "jcr_quartile": (row.get("jcr_quartile") or "").strip(),
                "cas_partition": (row.get("cas_partition") or "").strip(),
            }
            if issn:
                by_issn.setdefault(issn, entry)
            if name:
                by_name.setdefault(name, entry)
    return by_issn, by_name


def enrich(record, by_issn, by_name):
    """按 ISSN（优先）或期刊名匹配，把指标写回 record。"""
    issn = _norm(record.get("issn", ""))
    name = _norm(record.get("journal", ""))
    m = None
    if issn and issn in by_issn:
        m = by_issn[issn]
    elif name and name in by_name:
        m = by_name[name]
    if m:
        if not record.get("impact_factor") and m["impact_factor"]:
            record["impact_factor"] = m["impact_factor"]
        if not record.get("jcr_quartile") and m["jcr_quartile"]:
            record["jcr_quartile"] = m["jcr_quartile"]
        if not record.get("cas_partition") and m["cas_partition"]:
            record["cas_partition"] = m["cas_partition"]
    return record


def enrich_all(records, path=None):
    by_issn, by_name = load(path)
    if not by_issn and not by_name:
        return records
    for r in records:
        enrich(r, by_issn, by_name)
    return records
