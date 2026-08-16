"""从 PubMed / OpenAlex / Crossref / Semantic Scholar / WoS(可选) / 微信公众号RSS 收集文献，输出归一化 JSONL。

用法：
    python scripts/collect.py --since 7 [--out data/raw.jsonl] [--config config/config.yaml]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.parse

from common import (DATA_DIR, load_config, http_get_json, http_get_text,
                    norm_record, slugify, strip_tags)


def _query_terms(cfg) -> list:
    p = cfg.get("profile", {})
    terms = (p.get("keywords") or []) + (p.get("methods") or []) + (p.get("databases") or [])
    return [t for t in terms if t] or [""]


# ---------------- PubMed ----------------
def _parse_pubmed_abstracts(xml):
    """从 efetch XML 解析 PMID -> 摘要文本。"""
    abs_map = {}
    for m in re.finditer(r"<PubmedArticle>.*?</PubmedArticle>", xml, re.S):
        block = m.group(0)
        pmid = re.search(r"<PMID[^>]*>(\d+)</PMID>", block)
        ab = re.search(r"<Abstract>(.*?)</Abstract>", block, re.S)
        if pmid and ab:
            text = re.sub(r"\s+", " ", strip_tags(ab.group(1))).strip()
            abs_map[pmid.group(1)] = text
    return abs_map


def pubmed(cfg, since_days):
    n = int(cfg["sources"]["pubmed"].get("max_results", 50))
    email = cfg.get("profile", {}).get("email", "")
    out = []
    for kw in _query_terms(cfg):
        params = {
            "db": "pubmed", "term": kw, "retmax": n,
            "sort": "date", "datetype": "pdat", "reldate": since_days,
            "retmode": "json", "tool": "literature-lab", "email": email or "",
        }
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urllib.parse.urlencode(params)
        data = http_get_json(url)
        ids = data.get("esearchresult", {}).get("idlist", [])
        if not ids:
            continue
        time.sleep(0.4)
        sum_url = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?"
                   + urllib.parse.urlencode({"db": "pubmed", "id": ",".join(ids), "retmode": "json"}))
        summ = http_get_json(sum_url).get("result", {})
        time.sleep(0.4)
        abs_url = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?"
                   + urllib.parse.urlencode({"db": "pubmed", "id": ",".join(ids),
                                             "rettype": "abstract", "retmode": "xml"}))
        xml = http_get_text(abs_url)
        abs_map = _parse_pubmed_abstracts(xml)
        for pid in ids:
            r = summ.get(pid, {})
            if not r:
                continue
            doi = ""
            for a in r.get("articleids", []):
                if a.get("idtype") == "doi":
                    doi = a.get("value", "")
            if not doi and r.get("elocationid", "").startswith("10."):
                doi = r["elocationid"]
            spd = r.get("sortpubdate", "") or ""
            year = int(spd[:4]) if spd[:4].isdigit() else None
            rec = norm_record({
                "title": r.get("title", ""),
                "abstract": abs_map.get(pid, ""),
                "authors": [a.get("name", "") for a in r.get("authors", [])],
                "year": year,
                "journal": r.get("source", "") or r.get("fulljournalname", ""),
                "doi": doi,
                "pmid": pid,
                "issn": r.get("issn", "") or r.get("essn", ""),
                "url": "https://pubmed.ncbi.nlm.nih.gov/" + pid + "/",
                "published_date": spd.replace("/", "-").split(" ")[0] if spd else "",
            }, "pubmed")
            out.append(rec)
    return out


# ---------------- OpenAlex ----------------
def _oa_abstract(inv):
    if not inv:
        return ""
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos))


def openalex(cfg, since_days):
    n = int(cfg["sources"]["openalex"].get("max_results", 50))
    since = (dt.date.today() - dt.timedelta(days=since_days)).isoformat()
    email = cfg.get("profile", {}).get("email", "")
    out = []
    for kw in _query_terms(cfg):
        params = {
            "search": kw,
            "filter": "from_publication_date:" + since + ",type:article",
            "per-page": n,
            "mailto": email or "",
        }
        url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
        data = http_get_json(url)
        for w in data.get("results", []):
            src = w.get("primary_location") or {}
            src2 = src.get("source") or {}
            rec = norm_record({
                "title": w.get("title") or w.get("display_name") or "",
                "abstract": _oa_abstract(w.get("abstract_inverted_index")),
                "authors": [a.get("author", {}).get("display_name", "") for a in (w.get("authorships") or [])],
                "year": w.get("publication_year"),
                "journal": src2.get("display_name", ""),
                "doi": w.get("doi", ""),
                "issn": src2.get("issn_l", "") or ((src2.get("issn") or [""])[0]),
                "url": w.get("doi") or w.get("id", ""),
                "pdf_url": (w.get("open_access") or {}).get("oa_url", ""),
                "keywords": [c.get("display_name", "") for c in (w.get("concepts") or [])[:6]],
                "published_date": w.get("publication_date", ""),
                "citations": w.get("cited_by_count"),
                "is_open_access": (w.get("open_access") or {}).get("is_oa", False),
            }, "openalex")
            out.append(rec)
    return out


# ---------------- Crossref ----------------
def crossref(cfg, since_days):
    n = int(cfg["sources"]["crossref"].get("max_results", 50))
    since = (dt.date.today() - dt.timedelta(days=since_days)).isoformat()
    email = cfg.get("profile", {}).get("email", "")
    out = []
    for kw in _query_terms(cfg):
        params = {
            "query": kw,
            "filter": "from-pub-date:" + since + ",type:journal-article",
            "rows": n,
            "mailto": email or "",
        }
        url = "https://api.crossref.org/works?" + urllib.parse.urlencode(params)
        data = http_get_json(url)
        for it in data.get("message", {}).get("items", []):
            title = (it.get("title") or [""])[0]
            dp = (it.get("published") or {}).get("date-parts", [[None]])
            year = dp[0][0] if dp and dp[0] and dp[0][0] else None
            journal = (it.get("container-title") or [""])[0]
            pdf = ""
            for link in (it.get("link") or []):
                if link.get("content-type") in ("application/pdf", "text/xml"):
                    pdf = link.get("URL", "")
                    break
            rec = norm_record({
                "title": title,
                "abstract": strip_tags(it.get("abstract") or ""),
                "authors": [(a.get("given", "") + " " + a.get("family", "")).strip() for a in (it.get("author") or [])],
                "year": year,
                "journal": journal,
                "doi": it.get("DOI", ""),
                "issn": (it.get("ISSN") or [""])[0],
                "url": it.get("URL", "") or ("https://doi.org/" + it.get("DOI", "")),
                "pdf_url": pdf,
                "citations": it.get("is-referenced-by-count"),
                "published_date": "-".join(str(x) for x in (dp[0] if dp else []) if x),
            }, "crossref")
            out.append(rec)
    return out


# ---------------- Semantic Scholar ----------------
def semantic_scholar(cfg, since_days):
    n = int(cfg["sources"]["semantic_scholar"].get("max_results", 30))
    out = []
    fields = "title,abstract,authors,year,venue,externalIds,url,openAccessPdf,citationCount,publicationDate"
    for kw in _query_terms(cfg):
        params = {"query": kw, "fields": fields, "limit": n}
        url = "https://api.semanticscholar.org/graph/v1/paper/search?" + urllib.parse.urlencode(params)
        data = http_get_json(url)
        for p in data.get("data", []):
            ext = p.get("externalIds") or {}
            pdf = (p.get("openAccessPdf") or {}).get("url", "")
            rec = norm_record({
                "title": p.get("title", ""),
                "abstract": p.get("abstract") or "",
                "authors": [a.get("name", "") for a in (p.get("authors") or [])],
                "year": p.get("year"),
                "journal": p.get("venue", ""),
                "doi": ext.get("DOI", ""),
                "pmid": ext.get("PubMed", ""),
                "url": p.get("url", ""),
                "pdf_url": pdf,
                "citations": p.get("citationCount"),
                "published_date": p.get("publicationDate", ""),
                "is_open_access": bool(pdf),
            }, "semantic_scholar")
            out.append(rec)
    return out


# ---------------- Web of Science (可选插件) ----------------
def wos(cfg, since_days):
    w = cfg.get("sources", {}).get("wos", {})
    if not (w.get("enabled") and w.get("api_key")):
        return []
    base = w.get("base_url", "https://api.clarivate.com/apis/wos-starter/v1")
    out = []
    for kw in _query_terms(cfg):
        url = base + "/documents?" + urllib.parse.urlencode({"db": "WOS", "q": kw, "limit": 30})
        data = http_get_json(url, headers={"X-ApiKey": w["api_key"], "Accept": "application/json"})
        for h in data.get("hits", []):
            src = h.get("source", {}) or {}
            cit = h.get("citations") or [{}]
            rec = norm_record({
                "title": h.get("title", ""),
                "authors": [a.get("displayName", "") for a in (h.get("names", {}) or {}).get("authors", [])],
                "year": src.get("publishYear"),
                "journal": src.get("sourceTitle", ""),
                "doi": (h.get("identifiers") or {}).get("doi", ""),
                "issn": (h.get("identifiers") or {}).get("issn", ""),
                "url": (h.get("links") or {}).get("record", ""),
                "published_date": src.get("publishDate", ""),
                "citations": cit[0].get("count") if cit else None,
            }, "wos")
            out.append(rec)
    return out


# ---------------- 微信公众号 RSS ----------------
def wechat(cfg, since_days):
    w = cfg.get("sources", {}).get("wechat_rss", {})
    if not (w.get("enabled") and w.get("feed_urls")):
        return []
    try:
        import feedparser
    except ImportError:
        print("[wechat] 未安装 feedparser，跳过（pip install feedparser）。")
        return []
    out = []
    since = dt.datetime.now() - dt.timedelta(days=since_days)
    for fu in w["feed_urls"]:
        d = feedparser.parse(fu)
        for e in d.get("entries", []):
            pub = None
            try:
                pub = dt.datetime(*e.published_parsed[:6])
            except Exception:
                pub = None
            if pub and pub < since:
                continue
            rec = norm_record({
                "title": e.get("title", ""),
                "abstract": strip_tags(e.get("summary", ""))[:2000],
                "url": e.get("link", ""),
                "published_date": pub.isoformat() if pub else "",
                "year": pub.year if pub else None,
            }, "wechat")
            out.append(rec)
    return out


SOURCES = [
    ("pubmed", pubmed),
    ("openalex", openalex),
    ("crossref", crossref),
    ("semantic_scholar", semantic_scholar),
    ("wos", wos),
    ("wechat_rss", wechat),
]


def _merge_record(base, other):
    """把 other 的非空字段补进 base（跨源去重时保留更完整的信息）。"""
    for k in ("abstract", "pdf_url", "doi", "pmid", "url", "published_date", "journal"):
        if not base.get(k) and other.get(k):
            base[k] = other[k]
    for k in ("authors", "keywords"):
        if not base.get(k) and other.get(k):
            base[k] = other[k]
    if base.get("citations") is None and other.get("citations") is not None:
        base["citations"] = other["citations"]
    if base.get("year") is None and other.get("year") is not None:
        base["year"] = other["year"]
    if not base.get("journal_tier") and other.get("journal_tier"):
        base["journal_tier"] = other["journal_tier"]


def collect_all(cfg, since_days):
    srcs = cfg.get("sources", {})
    merged = {}
    for name, fn in SOURCES:
        if not srcs.get(name, {}).get("enabled"):
            continue
        try:
            recs = fn(cfg, since_days)
            print(f"[{name}] {len(recs)} 条")
        except Exception as e:
            print(f"[{name}] 错误: {e}")
            continue
        for r in recs:
            rid = r["id"]
            if rid in merged:
                _merge_record(merged[rid], r)
            else:
                merged[rid] = r
    return list(merged.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", type=int, default=None, help="最近 N 天")
    ap.add_argument("--out", default=os.path.join(DATA_DIR, "raw.jsonl"))
    ap.add_argument("--config", default=None)
    args = ap.parse_args()
    cfg = load_config(args.config)
    since = args.since if args.since is not None else cfg.get("schedule", {}).get("since_days", 7)
    recs = collect_all(cfg, since)
    seen, ded = set(), []
    for r in recs:
        if r["id"] not in seen:
            seen.add(r["id"])
            ded.append(r)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for r in ded:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"共 {len(ded)} 条（去重后）写入 {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
